package uvt.orar.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientRequestException;
import org.springframework.web.reactive.function.client.WebClientResponseException;
import reactor.core.publisher.Mono;
import reactor.core.scheduler.Schedulers;
import reactor.util.retry.Retry;
import uvt.orar.dto.OllamaExtractionResult;
import uvt.orar.dto.TimeslotDTO;
import uvt.orar.model.AvailabilityConstraint;
import uvt.orar.ollama.OllamaRequest;
import uvt.orar.ollama.OllamaResponse;

import java.time.Duration;
import java.util.*;
import java.util.concurrent.TimeoutException;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Slf4j
@Service
@RequiredArgsConstructor
public class OllamaClientService {

    private final WebClient webClient;
    private final ObjectMapper objectMapper;
    private final TextPreprocessorService preprocessor;
    private final ConstraintTextSupportService textSupport;

    @Value("${ollama.base-url}")
    private String ollamaBaseUrl;

    @Value("${ollama.model}")
    private String model;

    @Value("${ollama.timeout:120000}")
    private long timeout;

    @Value("${nlp.max-retries:3}")
    private int maxRetries;

    public Mono<OllamaExtractionResult> extractConstraints(String restrictionsText, String informationText) {
        return extractConstraints(restrictionsText, informationText, model);
    }

    public Mono<OllamaExtractionResult> extractConstraints(
            String restrictionsText,
            String informationText,
            String modelName
    ) {

        return preprocessor.preprocess(restrictionsText, informationText)

                .flatMap(preprocessedText -> {
                    int promptChars = preprocessedText.length();

                    if (preprocessedText.trim().isEmpty()) {
                        log.warn("Empty combined text, returning empty constraints");
                        return Mono.just(OllamaExtractionResult.builder()
                                .constraints(new ArrayList<>())
                                .modelName(modelName)
                                .promptChars(promptChars)
                                .rawResponseChars(0)
                                .jsonValid(true)
                                .emptyOutput(true)
                                .success(true)
                                .build());
                    }

                    log.debug("Preprocessed text:\n{}", preprocessedText);

                    String prompt = buildPrompt(preprocessedText);

                    OllamaRequest request = OllamaRequest.builder()
                            .model(modelName)
                            .prompt(prompt)
                            .stream(false)
                            .options(OllamaRequest.OllamaOptions.builder()
                                    .temperature(0.2)
                                    .numPredict(4096)
                                    .topP(0.9)
                                    .topK(40)
                                    .build())
                            .build();

                    log.info("Sending request to Ollama at: {}", ollamaBaseUrl + "/api/generate");

                    return webClient.post()
                            .uri(ollamaBaseUrl + "/api/generate")
                            .bodyValue(request)
                            .retrieve()
                            .bodyToMono(OllamaResponse.class)
                            .timeout(Duration.ofMillis(timeout))
                            .doOnSubscribe(s -> log.info("Starting Ollama request..."))
                            .doOnNext(response -> log.info("Received Ollama response ({} chars)",
                                    response.getResponse() != null ? response.getResponse().length() : 0))
                            .retryWhen(Retry.backoff(maxRetries, Duration.ofSeconds(2))
                                    .maxBackoff(Duration.ofSeconds(10))
                                    .filter(this::isRetryableError)
                                    .doBeforeRetry(retrySignal -> {
                                        Throwable failure = retrySignal.failure();
                                        log.warn("Retrying Ollama request (attempt {}): {}",
                                                retrySignal.totalRetries() + 1,
                                                failure.getClass().getSimpleName() + " - " + failure.getMessage());
                                    }))
                            .flatMap(response -> parseConstraints(response, preprocessedText, promptChars, modelName))
                            .doOnError(error -> log.error("Ollama request failed after retries: {} - {}",
                                    error.getClass().getSimpleName(), error.getMessage()))
                            .onErrorResume(error -> handleError(error, promptChars, modelName));
                })
                .subscribeOn(Schedulers.boundedElastic());
    }

    public String getConfiguredModel() {
        return model;
    }

    private String buildPrompt(String text) {
        return String.format("""
          Extract teacher availability constraints from Romanian text.
          Return ONLY a valid JSON array. Each line starting with "-" is a separate constraint. For each "-" extract a constraint.
    
          TEXT:
          %s
    
          === RULES ===
    
          1. DAYS - ALWAYS translate Romanian to English:
             luni -> Monday
             lunea -> Monday
             marti-> Tuesday
             marți-> Tuesday
             marțea-> Tuesday
             martea -> Tuesday
             miercuri-> Wednesday
             miercurea -> Wednesday
             joi -> Thursday
             joia -> Thursday
             vineri-> Friday
             vinerea -> Friday
    
             IMPORTANT: If you see ANY Romanian day name, you MUST include it in "days" array in English!

          2. TIME INTERVALS:
             - Extract as: {"startHour":"HH:MM", "endHour":"HH:MM"}
             - endHour can not be 24:00 or 00:00 -> map it like 23:59
             - "dupa HH:MM" means AVAILABLE only after HH:MM -> availability = 2
             - "nu dupa HH:MM" means NOT available after HH:MM -> availability = -1
             - "incepand cu HH:MM" means AVAILABLE after HH:MM -> availability = 2
             - "nu incepand cu HH:MM" means NOT AVAILABLE after HH:MM -> availability = -1
             - "cel mai devreme de la HH:MM" means AVAILABLE after HH:MM -> availability = 2
             - "nu de la HH:MM" means NOT AVAILABLE at HH:MM -> availability = -1
             - "restrictii HH:MM" means NOT AVAILABLE at HH:MM -> availability = -1
             - "restrictii in DayName" means NOT AVAILABLE at HH:MM -> availability = -1
    
          3. AVAILABILITY - VERY IMPORTANT!:
             -1 = NOT available: "nu pot", "nu pot preda", "nu tin ore", "indisponibil", "nu doresc", "pe cat posibil nu", "fara ore", "fara cursuri", "fara laboratoare", "sa nu puneti", "de preferat sa nu fie", "sa nu fie", "restrictii"
             1 = PREFERS: "ar fi bine", "de preferat", "aș dori", "doresc", "preferabil"
             2 = ONLY available: "doar", "sunt disponibil doar"
      
          4. FORMAT
             - if only the day is specified like "nu in DayName" -> { "days": ["DayName", ...], "intervals": [], ...}
             - if only the intervals are specified like "nu in Interval1" -> { "days": [], "intervals": ["Interval1", ...], ...}

          CRITICAL RULES:
          - ALWAYS provide "reason" and "confidence"
          - ALWAYS check for Romanian day names (luni, marti, miercuri, joi, vineri)
          - ALWAYS translate them to English in the "days" array
          - If a line contains an activity (meeting, decanat, sedinta, intalniri, cercetare, examen, conferinta etc.)
                      then the teacher is NOT available during that time -> availability = -1
          - "cu exceptia", "mai putin", "in afara de", "exceptand", "restrictii" indicate EXCLUDED days or intervals -> availability = -1 for that day
          - If a line contains one of these formulations "nu pot", "nu pot preda", "nu tin ore", "indisponibil", "nu doresc",
                      "pe cat posibil nu", "fara ore", "fara cursuri", "fara laboratoare", "sa nu puneti", "de preferat sa nu fie",
                      "sa nu fie", then the teacher is NOT available -> availability = -1
          - If a line contains "restrictii" then the teacher is NOT available -> availability = -1
          - Each line = one JSON object

          OUTPUT:
          [
             {
                "days": ["DayName", ...],
                "intervals": [{"startHour":"HH:MM","endHour":"HH:MM"}],
                "availability": -1 or 1 or 2,
                "reason": "reason extracted from text",
                "confidence": 0.1-1.0
             }
          ]
          Return ONLY the JSON array, no other text.
      """, text);
    }

    private boolean isRetryableError(Throwable throwable) {
        if (throwable instanceof TimeoutException) {
            log.warn("Timeout occurred, will retry");
            return true;
        }
        if (throwable instanceof WebClientRequestException) {
            log.warn("Connection error occurred, will retry");
            return true;
        }
        if (throwable instanceof WebClientResponseException webClientEx) {
            int statusCode = webClientEx.getStatusCode().value();
            if (statusCode >= 400 && statusCode < 500) {
                log.error("Client error ({}), will not retry: {}",
                        statusCode, webClientEx.getMessage());
                return false;
            }
            log.warn("Server error ({}), will retry", statusCode);
            return true;
        }
        return false;
    }

    private Mono<OllamaExtractionResult> handleError(Throwable error, int promptChars, String modelName) {
        if (error instanceof TimeoutException) {
            log.error("Ollama request timed out after {} ms. Is Ollama running and is the model loaded?", timeout);
        } else if (error instanceof WebClientRequestException) {
            log.error("Cannot connect to Ollama at {}. Is Ollama running?", ollamaBaseUrl);
        } else if (error instanceof WebClientResponseException webClientEx) {
            log.error("Ollama returned error {}: {}",
                    webClientEx.getStatusCode(), webClientEx.getResponseBodyAsString());
        } else {
            log.error("Unexpected error during Ollama request", error);
        }

        log.warn("Returning empty constraints due to error");
        return Mono.just(OllamaExtractionResult.builder()
                .constraints(List.of())
                .modelName(modelName)
                .promptChars(promptChars)
                .rawResponseChars(0)
                .jsonValid(false)
                .emptyOutput(true)
                .success(false)
                .errorMessage(error.getMessage())
                .build());
    }

    private Mono<OllamaExtractionResult> parseConstraints(
            OllamaResponse response,
            String preprocessedText,
            int promptChars,
            String modelName
    ) {
        try {
            if (response == null || response.getResponse() == null || response.getResponse().trim().isEmpty()) {
                log.warn("Empty response from Ollama");
                return Mono.just(buildExtractionResult(
                        response,
                        promptChars,
                        0,
                        List.of(),
                        false,
                        true,
                        false,
                        "Empty response from Ollama",
                        modelName
                ));
            }

            String rawResponse = response.getResponse();
            log.debug("Raw Ollama response: {}", rawResponse.substring(0, Math.min(200, rawResponse.length())));

            String jsonResponse = extractJsonFromResponse(rawResponse);

            if (jsonResponse == null || jsonResponse.trim().isEmpty()) {
                log.warn("No JSON found in response");
                return Mono.just(buildExtractionResult(
                        response,
                        promptChars,
                        rawResponse.length(),
                        List.of(),
                        false,
                        true,
                        false,
                        "No JSON found in model response",
                        modelName
                ));
            }

            List<AvailabilityConstraint> constraints = objectMapper.readValue(
                    jsonResponse,
                    new TypeReference<List<AvailabilityConstraint>>() {
                    }
            );

            List<String> sourceLines = preprocessedText.lines()
                    .map(String::trim)
                    .filter(s -> !s.isEmpty())
                    .toList();

            for (int i = 0; i < constraints.size(); i++) {
                AvailabilityConstraint c = constraints.get(i);

                if (c.getDays() == null) {
                    c.setDays(new ArrayList<>());
                }
                if (c.getIntervals() == null) {
                    c.setIntervals(new ArrayList<>());
                }

                String sourceLine = textSupport.resolveSourceLine(c, sourceLines, i, constraints.size());
                reconcileStructuredFields(c, sourceLine);
            }

            constraints = constraints.stream()
                    .peek(constraint -> {
                        if (constraint.getDays() == null) {
                            constraint.setDays(new ArrayList<>());
                        }
                        if (constraint.getIntervals() == null) {
                            constraint.setIntervals(new ArrayList<>());
                        }
                    })
                    .filter(constraint -> {
                        boolean hasValidAvailability = (constraint.getAvailability() == -1 ||
                                constraint.getAvailability() == 0 ||
                                constraint.getAvailability() == 1 ||
                                constraint.getAvailability() == 2);

                        boolean hasData = (!constraint.getDays().isEmpty()) ||
                                (!constraint.getIntervals().isEmpty());

                        boolean isSingleFullDayWithoutDays = isIsSingleFullDayWithoutDays(constraint);

                        if (isSingleFullDayWithoutDays) {
                            log.warn("Skipping invalid constraint: no days + full-day interval -> {}", constraint);
                            return false;
                        }

                        return hasValidAvailability && hasData;
                    })
                    .toList();

            constraints = dropRedundantConstraints(constraints);

            log.info("Successfully parsed {} valid constraints", constraints.size());
            return Mono.just(buildExtractionResult(
                    response,
                    promptChars,
                    rawResponse.length(),
                    constraints,
                    true,
                    constraints.isEmpty(),
                    true,
                    null,
                    modelName
            ));

        } catch (Exception e) {
            log.error("Failed to parse constraints", e);
            return Mono.just(buildExtractionResult(
                    response,
                    promptChars,
                    response != null && response.getResponse() != null ? response.getResponse().length() : 0,
                    List.of(),
                    false,
                    true,
                    false,
                    e.getMessage(),
                    modelName
            ));
        }
    }

    private OllamaExtractionResult buildExtractionResult(
            OllamaResponse response,
            int promptChars,
            int rawResponseChars,
            List<AvailabilityConstraint> constraints,
            boolean jsonValid,
            boolean emptyOutput,
            boolean success,
            String errorMessage,
            String modelName
    ) {
        return OllamaExtractionResult.builder()
                .constraints(constraints)
                .modelName(response != null && response.getModel() != null ? response.getModel() : modelName)
                .promptChars(promptChars)
                .rawResponseChars(rawResponseChars)
                .promptEvalCount(response != null ? response.getPromptEvalCount() : null)
                .evalCount(response != null ? response.getEvalCount() : null)
                .ollamaTotalDurationMs(nanosToMillis(response != null ? response.getTotalDuration() : null))
                .ollamaLoadDurationMs(nanosToMillis(response != null ? response.getLoadDuration() : null))
                .jsonValid(jsonValid)
                .emptyOutput(emptyOutput)
                .success(success)
                .errorMessage(errorMessage)
                .build();
    }

    private Long nanosToMillis(Long nanos) {
        return nanos == null ? null : nanos / 1_000_000L;
    }

    private String extractJsonFromResponse(String response) {
        if (response == null || response.trim().isEmpty()) {
            return null;
        }

        String trimmed = response.trim();
        trimmed = trimmed.replaceAll("```(?:json)?\\s*", "").replaceAll("```", "");
        trimmed = trimmed.trim();

        int arrayStart = trimmed.indexOf('[');
        int arrayEnd = trimmed.lastIndexOf(']');

        if (arrayStart != -1 && arrayEnd != -1 && arrayEnd > arrayStart) {
            String jsonArray = trimmed.substring(arrayStart, arrayEnd + 1);

            int bracketCount = 0;
            for (char c : jsonArray.toCharArray()) {
                if (c == '[') bracketCount++;
                else if (c == ']') bracketCount--;
                if (bracketCount < 0) break;
            }

            if (bracketCount == 0) {
                log.debug("Extracted valid JSON array: {} chars", jsonArray.length());
                return jsonArray;
            }
        }

        int braceCount = 0;
        int startIndex = -1;
        int endIndex = -1;

        for (int i = 0; i < trimmed.length(); i++) {
            char c = trimmed.charAt(i);
            if (c == '{') {
                if (braceCount == 0) startIndex = i;
                braceCount++;
            } else if (c == '}') {
                braceCount--;
                if (braceCount == 0 && startIndex != -1) {
                    endIndex = i;
                    break;
                }
            }
        }

        if (startIndex != -1 && endIndex != -1) {
            String jsonObject = trimmed.substring(startIndex, endIndex + 1);
            log.debug("Extracted single object, wrapping in array");
            return "[" + jsonObject + "]";
        }

        log.warn("Could not extract valid JSON from response");
        return null;
    }

    private static boolean isIsSingleFullDayWithoutDays(AvailabilityConstraint constraint) {
        boolean hasDays = !constraint.getDays().isEmpty();
        return !hasDays &&
                constraint.getIntervals() != null &&
                constraint.getIntervals().size() == 1 &&
                "00:00".equals(constraint.getIntervals().get(0).getStartHour()) &&
                "23:59".equals(constraint.getIntervals().get(0).getEndHour());
    }

    private void reconcileStructuredFields(AvailabilityConstraint constraint, String sourceLine) {
        if (sourceLine == null || sourceLine.isBlank()) {
            return;
        }

        List<String> sourceDays = textSupport.extractDaysFromText(sourceLine);
        if (!sourceDays.isEmpty()) {
            constraint.setDays(sourceDays);
        }

        List<TimeslotDTO> sourceIntervals = textSupport.extractIntervalsFromText(sourceLine);
        if (!sourceIntervals.isEmpty()) {
            if (sourceDays.isEmpty()) {
                // The source line contains only an interval, so any model-invented day should be removed.
                constraint.setDays(new ArrayList<>());
            }
            if (constraint.getIntervals().isEmpty()) {
                constraint.setIntervals(sourceIntervals);
            }
        } else if (!sourceDays.isEmpty()) {
            constraint.setIntervals(new ArrayList<>());
        }
    }

    private List<AvailabilityConstraint> dropRedundantConstraints(List<AvailabilityConstraint> constraints) {
        List<AvailabilityConstraint> filtered = new ArrayList<>();

        for (AvailabilityConstraint candidate : constraints) {
            if (isRedundant(candidate, constraints)) {
                log.debug("Dropping redundant constraint: {}", candidate);
                continue;
            }
            filtered.add(candidate);
        }

        return filtered;
    }

    private boolean isRedundant(AvailabilityConstraint candidate, List<AvailabilityConstraint> constraints) {
        for (AvailabilityConstraint other : constraints) {
            if (candidate == other) {
                continue;
            }

            if (!Objects.equals(candidate.getAvailability(), other.getAvailability())) {
                continue;
            }

            if (!sameIntervals(candidate.getIntervals(), other.getIntervals())) {
                continue;
            }

            Set<String> candidateDays = new LinkedHashSet<>(candidate.getDays() == null ? List.of() : candidate.getDays());
            Set<String> otherDays = new LinkedHashSet<>(other.getDays() == null ? List.of() : other.getDays());

            if (!otherDays.containsAll(candidateDays)) {
                continue;
            }

            boolean stricterCoverage = otherDays.size() > candidateDays.size();
            boolean sameCoverageHigherConfidence =
                    otherDays.size() == candidateDays.size() &&
                            Objects.equals(otherDays, candidateDays) &&
                            safeConfidence(other) >= safeConfidence(candidate);

            if (stricterCoverage || sameCoverageHigherConfidence) {
                return true;
            }
        }

        return false;
    }

    private boolean sameIntervals(List<TimeslotDTO> left, List<TimeslotDTO> right) {
        return Objects.equals(normalizeIntervals(left), normalizeIntervals(right));
    }

    private List<String> normalizeIntervals(List<TimeslotDTO> intervals) {
        if (intervals == null || intervals.isEmpty()) {
            return List.of();
        }

        return intervals.stream()
                .map(interval -> {
                    String start = interval.getStartHour() == null ? "" : interval.getStartHour();
                    String end = interval.getEndHour() == null ? "" : interval.getEndHour();
                    return start + "->" + end;
                })
                .sorted()
                .toList();
    }

    private double safeConfidence(AvailabilityConstraint constraint) {
        return constraint.getConfidence() == null ? 0.0 : constraint.getConfidence();
    }
}
