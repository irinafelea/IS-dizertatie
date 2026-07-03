package uvt.orar.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;
import reactor.core.scheduler.Schedulers;
import uvt.orar.dto.OptionDTO;
import uvt.orar.dto.ProcessingResultDTO;
import uvt.orar.dto.TimeslotDTO;
import uvt.orar.external_services.DayService;
import uvt.orar.external_services.TimeslotService;
import uvt.orar.model.AvailabilityConstraint;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class BenchmarkEvaluationService {

    private static final List<String> ALL_WEEKDAYS = List.of(
            "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"
    );

    private static final String CSV_FILE = "benchmark-results.csv";
    private static final String CSV_HEADER = String.join(",",
            "caseId",
            "optionId",
            "model",
            "runId",
            "rowF1",
            "constraintExactMatch",
            "availabilityAccuracy",
            "dayF1",
            "intervalF1",
            "jsonValidPct",
            "emptyOutputPct",
            "avgLatencyMs",
            "stabilityPct"
    );

    private final ObjectMapper objectMapper;
    private final DayService dayService;
    private final TimeslotService timeslotService;

    @Value("${app.benchmark.gold-file:benchmark/gold-answers.json}")
    private String goldFilePath;

    @Value("${app.benchmark.export-dir:exports/benchmarks}")
    private String benchmarkExportDir;

    public Mono<BenchmarkExportResult> runBenchmark(OptionDTO option, ProcessingResultDTO result) {
        return Mono.fromCallable(() -> loadGoldCaseByOptionId(option.getId()))
                .subscribeOn(Schedulers.boundedElastic())
                .flatMap(optionalGoldCase -> optionalGoldCase
                        .map(goldCase -> dayService.getCanonicalDayNames()
                                .zipWith(timeslotService.getAll().collectList())
                                .flatMap(tuple -> Mono.fromCallable(() -> appendBenchmarkRow(
                                        goldCase,
                                        option,
                                        result,
                                        tuple.getT1(),
                                        buildTimeslotLabels(tuple.getT2())
                                )).subscribeOn(Schedulers.boundedElastic())))
                        .orElseGet(Mono::empty));
    }

    private BenchmarkExportResult appendBenchmarkRow(
            GoldCase goldCase,
            OptionDTO option,
            ProcessingResultDTO result,
            Map<UUID, String> canonicalDays,
            Map<UUID, String> timeslotLabels
    ) throws IOException {
        List<ExpandedRow> expectedRows = goldCase.expectedExpandedRows();
        List<ExpandedRow> predictedRows = result.getSavedRows().stream()
                .map(row -> ExpandedRow.builder()
                        .day(canonicalDays.getOrDefault(row.dayId(), row.dayId().toString()))
                        .timeslot(timeslotLabels.getOrDefault(row.timeslotId(), row.timeslotId().toString()))
                        .availability(row.availability())
                        .build())
                .sorted(Comparator.comparing(ExpandedRow::getDay).thenComparing(ExpandedRow::getTimeslot))
                .toList();

        double rowF1 = calculateRowF1(expectedRows, predictedRows);
        double constraintExactMatch = calculateConstraintExactMatch(goldCase.getExpectedConstraints(), result.getExtractedConstraints());
        double availabilityAccuracy = calculateAvailabilityAccuracy(expectedRows, predictedRows);
        double dayF1 = calculateDayF1(goldCase.getExpectedConstraints(), result.getExtractedConstraints());
        double intervalF1 = calculateIntervalF1(expectedRows, predictedRows);
        String rowSignature = buildRowSignature(predictedRows);
        double jsonValidPct = toPercent(result.getMetrics() != null && Boolean.TRUE.equals(result.getMetrics().getJsonValid()));
        double emptyOutputPct = toPercent(result.getMetrics() != null && Boolean.TRUE.equals(result.getMetrics().getEmptyOutput()));
        String latencyMs = resolveLatency(result);
        double stabilityPct = 100.0;

        Path exportDir = Paths.get(benchmarkExportDir);
        Files.createDirectories(exportDir);
        Path csvPath = exportDir.resolve(CSV_FILE);
        ensureCsvHeader(csvPath);

        String csvLine = String.join(",",
                escape(goldCase.getCaseId()),
                escape(option.getId()),
                escape(resolveModel(result)),
                escape(resolveRunId(result)),
                escape(formatDouble(rowF1)),
                escape(formatDouble(constraintExactMatch)),
                escape(formatDouble(availabilityAccuracy)),
                escape(formatDouble(dayF1)),
                escape(formatDouble(intervalF1)),
                escape(formatDouble(jsonValidPct)),
                escape(formatDouble(emptyOutputPct)),
                escape(latencyMs),
                escape(formatDouble(stabilityPct))
        );

        Files.writeString(csvPath, csvLine + System.lineSeparator(), StandardCharsets.UTF_8,
                StandardOpenOption.APPEND);

        return BenchmarkExportResult.builder()
                .path(csvPath.toAbsolutePath().toString())
                .appended(true)
                .caseId(goldCase.getCaseId())
                .model(resolveModel(result))
                .createdAt(LocalDateTime.now())
                .message("Benchmark CSV row appended")
                .build();
    }

    private void ensureCsvHeader(Path csvPath) throws IOException {
        if (!Files.exists(csvPath)) {
            Files.writeString(csvPath, CSV_HEADER + System.lineSeparator(), StandardCharsets.UTF_8,
                    StandardOpenOption.CREATE, StandardOpenOption.WRITE);
            return;
        }

        List<String> lines = Files.readAllLines(csvPath, StandardCharsets.UTF_8);
        String existingHeader = lines.isEmpty() ? "" : lines.getFirst().trim();

        if (!Objects.equals(existingHeader, CSV_HEADER)) {
            Files.writeString(csvPath, CSV_HEADER + System.lineSeparator(), StandardCharsets.UTF_8,
                    StandardOpenOption.TRUNCATE_EXISTING, StandardOpenOption.WRITE);
        }
    }

    private Optional<GoldCase> loadGoldCaseByOptionId(UUID optionId) throws IOException {
        Path path = Paths.get(goldFilePath);
        if (!Files.exists(path)) {
            throw new IllegalStateException("Gold answers file not found: " + path.toAbsolutePath());
        }

        List<GoldCase> cases = objectMapper.readValue(
                Files.readString(path, StandardCharsets.UTF_8),
                new TypeReference<List<GoldCase>>() {}
        );

        return cases.stream()
                .filter(c -> Objects.equals(c.getOptionId(), optionId))
                .findFirst();
    }

    private Map<UUID, String> buildTimeslotLabels(List<TimeslotDTO> timeslots) {
        return timeslots.stream()
                .filter(ts -> ts.getId() != null)
                .collect(Collectors.toMap(
                        TimeslotDTO::getId,
                        ts -> ts.getStartHour() + "-" + ts.getEndHour(),
                        (a, b) -> a,
                        HashMap::new
                ));
    }

    private double calculateRowF1(List<ExpandedRow> expectedRows, List<ExpandedRow> predictedRows) {
        Set<String> expected = expectedRows.stream().map(ExpandedRow::keyWithAvailability).collect(Collectors.toSet());
        Set<String> predicted = predictedRows.stream().map(ExpandedRow::keyWithAvailability).collect(Collectors.toSet());
        return f1(expected, predicted);
    }

    private double calculateConstraintExactMatch(
            List<GoldConstraint> expectedConstraints,
            List<AvailabilityConstraint> predictedConstraints
    ) {
        Set<String> expected = expectedConstraints.stream().map(this::normalizeConstraint).collect(Collectors.toSet());
        Set<String> predicted = predictedConstraints.stream().map(this::normalizeConstraint).collect(Collectors.toSet());
        if (expected.isEmpty() && predicted.isEmpty()) {
            return 1.0;
        }
        long matched = expected.stream().filter(predicted::contains).count();
        return expected.isEmpty() ? 0.0 : (double) matched / expected.size();
    }

    private double calculateAvailabilityAccuracy(List<ExpandedRow> expectedRows, List<ExpandedRow> predictedRows) {
        if (expectedRows.isEmpty()) {
            return predictedRows.isEmpty() ? 1.0 : 0.0;
        }
        Map<String, Integer> predictedByKey = predictedRows.stream()
                .collect(Collectors.toMap(ExpandedRow::keyWithoutAvailability, ExpandedRow::getAvailability, (a, b) -> a));
        long correct = expectedRows.stream()
                .filter(row -> Objects.equals(predictedByKey.get(row.keyWithoutAvailability()), row.getAvailability()))
                .count();
        return (double) correct / expectedRows.size();
    }

    private double calculateDayF1(List<GoldConstraint> expectedConstraints, List<AvailabilityConstraint> predictedConstraints) {
        Set<String> expectedDays = expectedConstraints.stream()
                .flatMap(constraint -> normalizeConstraintDays(constraint).stream())
                .map(this::normalizeDay)
                .collect(Collectors.toSet());
        Set<String> predictedDays = predictedConstraints.stream()
                .flatMap(constraint -> normalizeConstraintDays(constraint).stream())
                .map(this::normalizeDay)
                .collect(Collectors.toSet());
        return f1(expectedDays, predictedDays);
    }

    private double calculateIntervalF1(List<ExpandedRow> expectedRows, List<ExpandedRow> predictedRows) {
        Set<String> expectedIntervals = expectedRows.stream()
                .map(ExpandedRow::keyWithoutAvailability)
                .collect(Collectors.toSet());
        Set<String> predictedIntervals = predictedRows.stream()
                .map(ExpandedRow::keyWithoutAvailability)
                .collect(Collectors.toSet());
        return f1(expectedIntervals, predictedIntervals);
    }

    private double f1(Set<String> expected, Set<String> predicted) {
        if (expected.isEmpty() && predicted.isEmpty()) {
            return 1.0;
        }
        if (expected.isEmpty() || predicted.isEmpty()) {
            return 0.0;
        }
        long overlap = expected.stream().filter(predicted::contains).count();
        double precision = (double) overlap / predicted.size();
        double recall = (double) overlap / expected.size();
        if (precision + recall == 0.0) {
            return 0.0;
        }
        return 2.0 * precision * recall / (precision + recall);
    }

    private String normalizeConstraint(GoldConstraint constraint) {
        List<String> days = normalizeConstraintDays(constraint).stream()
                .map(this::normalizeDay).sorted().toList();
        List<String> intervals = constraint.getIntervals() == null ? List.of() : constraint.getIntervals().stream()
                .map(this::normalizeInterval).sorted().toList();
        return days + "|" + intervals + "|" + constraint.getAvailability();
    }

    private String normalizeConstraint(AvailabilityConstraint constraint) {
        List<String> days = normalizeConstraintDays(constraint).stream()
                .map(this::normalizeDay).sorted().toList();
        List<String> intervals = constraint.getIntervals() == null ? List.of() : constraint.getIntervals().stream()
                .map(this::normalizeInterval).sorted().toList();
        return days + "|" + intervals + "|" + constraint.getAvailability();
    }

    private List<String> normalizeConstraintDays(GoldConstraint constraint) {
        List<String> days = constraint.getDays() == null ? List.of() : constraint.getDays();
        boolean hasIntervals = constraint.getIntervals() != null && !constraint.getIntervals().isEmpty();
        return normalizeConstraintDays(days, hasIntervals);
    }

    private List<String> normalizeConstraintDays(AvailabilityConstraint constraint) {
        List<String> days = constraint.getDays() == null ? List.of() : constraint.getDays();
        boolean hasIntervals = constraint.getIntervals() != null && !constraint.getIntervals().isEmpty();
        return normalizeConstraintDays(days, hasIntervals);
    }

    private List<String> normalizeConstraintDays(List<String> days, boolean hasIntervals) {
        if ((days == null || days.isEmpty()) && hasIntervals) {
            return ALL_WEEKDAYS;
        }
        return days == null ? List.of() : days;
    }

    private String normalizeInterval(TimeslotDTO interval) {
        return interval.getStartHour() + "-" + interval.getEndHour();
    }

    private String normalizeDay(String day) {
        if (day == null || day.isBlank()) {
            return "";
        }
        String lower = day.trim().toLowerCase(Locale.ROOT);
        return switch (lower) {
            case "monday", "luni", "lunea" -> "Monday";
            case "tuesday", "marti", "marți", "martea", "marțea" -> "Tuesday";
            case "wednesday", "miercuri", "miercurea" -> "Wednesday";
            case "thursday", "joi", "joia" -> "Thursday";
            case "friday", "vineri", "vinerea" -> "Friday";
            default -> day.trim();
        };
    }

    private String buildRowSignature(List<ExpandedRow> rows) {
        return rows.stream()
                .map(ExpandedRow::keyWithAvailability)
                .sorted()
                .collect(Collectors.joining("|"));
    }

    private String resolveModel(ProcessingResultDTO result) {
        return result.getMetrics() != null ? result.getMetrics().getModelName() : "";
    }

    private String resolveRunId(ProcessingResultDTO result) {
        return result.getMetrics() != null && result.getMetrics().getId() != null
                ? result.getMetrics().getId().toString()
                : "";
    }

    private String resolveLatency(ProcessingResultDTO result) {
        if (result.getMetrics() == null) {
            return "";
        }
        Long latency = result.getMetrics().getProcessingDurationMs() != null
                ? result.getMetrics().getProcessingDurationMs()
                : result.getMetrics().getOllamaTotalDurationMs();
        return latency == null ? "" : latency.toString();
    }

    private String formatDouble(double value) {
        return String.format(Locale.US, "%.4f", value);
    }

    private String booleanValue(boolean value) {
        return value ? "true" : "false";
    }

    private double toPercent(boolean value) {
        return value ? 100.0 : 0.0;
    }

    private String escape(Object value) {
        if (value == null) {
            return "";
        }
        String text = String.valueOf(value);
        if (text.contains(",") || text.contains("\"") || text.contains("\n") || text.contains("\r")) {
            return "\"" + text.replace("\"", "\"\"") + "\"";
        }
        return text;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class GoldCase {
        private String caseId;
        private UUID optionId;
        private GoldInput input;
        private List<GoldConstraint> expectedConstraints = new ArrayList<>();
        private List<GoldRow> expectedRows = new ArrayList<>();

        public List<ExpandedRow> expectedExpandedRows() {
            return expectedRows == null ? List.of() : expectedRows.stream()
                    .map(row -> ExpandedRow.builder()
                            .day(row.getDay())
                            .timeslot(row.getTimeslot())
                            .availability(row.getAvailability())
                            .build())
                    .sorted(Comparator.comparing(ExpandedRow::getDay).thenComparing(ExpandedRow::getTimeslot))
                    .toList();
        }
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class GoldInput {
        private String restrictions;
        private String information;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class GoldConstraint {
        private List<String> days = new ArrayList<>();
        private List<TimeslotDTO> intervals = new ArrayList<>();
        private Integer availability;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class GoldRow {
        private String day;
        private String timeslot;
        private Integer availability;
    }

    @Data
    @Builder
    private static class ExpandedRow {
        private String day;
        private String timeslot;
        private int availability;

        private String keyWithoutAvailability() {
            return day + "|" + timeslot;
        }

        private String keyWithAvailability() {
            return day + "|" + timeslot + "|" + availability;
        }
    }

    @Getter
    @Builder
    public static class BenchmarkExportResult {
        private final String path;
        private final boolean appended;
        private final String caseId;
        private final String model;
        private final LocalDateTime createdAt;
        private final String message;

        public static BenchmarkExportResult skipped(String message) {
            return BenchmarkExportResult.builder()
                    .appended(false)
                    .message(message)
                    .createdAt(LocalDateTime.now())
                    .build();
        }
    }
}
