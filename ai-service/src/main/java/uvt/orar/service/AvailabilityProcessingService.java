package uvt.orar.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;
import uvt.orar.dto.AvailabilityDTO;
import uvt.orar.dto.OptionDTO;
import uvt.orar.dto.OllamaExtractionResult;
import uvt.orar.dto.ProcessingResultDTO;
import uvt.orar.external_services.DayService;
import uvt.orar.external_services.TimeslotService;
import uvt.orar.model.AvailabilityConstraint;
import uvt.orar.model.ExtractionMetric;
import uvt.orar.model.TeacherAvailability;
import uvt.orar.repository.TeacherAvailabilityRepository;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class AvailabilityProcessingService {

    private final OllamaClientService ollamaClientService;
    private final TeacherAvailabilityRepository availabilityRepository;
    private final DayService dayService;
    private final TimeslotService timeslotService;
    private final BenchmarkEvaluationService benchmarkEvaluationService;

    @Value("${nlp.confidence-threshold}")
    private double confidenceThreshold;

    public Flux<AvailabilityDTO> getAll() {
        return availabilityRepository.findAll().map(this::toDto);
    }

    public Flux<AvailabilityDTO> getBySemesterIdAndDomainId(UUID semesterId, UUID domainId) {
        return availabilityRepository.getBySemesterIdAndDomainId(semesterId, domainId).map(this::toDto);
    }

    public Flux<AvailabilityDTO> getByOptionId(UUID optionId) {
        return availabilityRepository.findByOptionId(optionId).map(this::toDto);
    }

    private AvailabilityDTO toDto(TeacherAvailability e) {
        return new AvailabilityDTO(
                e.getTeacherId(),
                e.getDayId(),
                e.getTimeslotId(),
                e.getAvailability(),
                e.getReason(),
                e.getWeight()
        );
    }

    public Mono<ProcessingResultDTO> processTeacherOption(OptionDTO option) {
        long startedAtNanos = System.nanoTime();

        log.info("Processing teacher option: teacher={}, option={}",
                option.getTeacher().getEmail(), option.getId());

        return availabilityRepository.deleteByOptionId(option.getId())
                .then(ollamaClientService.extractConstraints(option.getRestrictions(), option.getInformation()))
                .doOnNext(result -> log.info("Extracted {} constraints for option {}",
                        result.getConstraints().size(), option.getId()))
                .flatMap(result -> {
                    List<AvailabilityConstraint> constraints = result.getConstraints();
                    List<AvailabilityConstraint> acceptedConstraints = filterAcceptedConstraints(constraints);

                    return Flux.fromIterable(acceptedConstraints)
                                .flatMap(c -> createAvailabilityRecords(option, c))
                                .collect(
                                        HashMap<String, TeacherAvailability>::new,
                                        (map, row) -> map.merge(
                                                buildAvailabilityKey(row),
                                                row,
                                                this::chooseStrongerConstraint
                                        )
                                )
                                .flatMapMany(map -> Flux.fromIterable(map.values()))
                                .flatMap(availabilityRepository::save)
                                .map(this::toDto)
                                .collectList()
                                .doOnNext(saved -> log.info("Saved {} availability rows for option {}", saved.size(), option.getId()))
                                .map(savedRows -> ProcessingResultDTO.builder()
                                        .extractedConstraints(constraints)
                                        .savedRows(savedRows)
                                        .metrics(buildMetrics(
                                                option,
                                                result,
                                                constraints.size(),
                                                acceptedConstraints.size(),
                                                savedRows.size(),
                                                true,
                                                null,
                                                startedAtNanos
                                        ))
                                        .build())
                                .flatMap(processingResult -> benchmarkEvaluationService.runBenchmark(option, processingResult)
                                        .defaultIfEmpty(BenchmarkEvaluationService.BenchmarkExportResult.skipped(
                                                "No gold answer found for option " + option.getId()
                                        ))
                                        .map(benchmarkResult -> {
                                            processingResult.setBenchmark(benchmarkResult);
                                            return processingResult;
                                        }));
                });
    }

    private List<AvailabilityConstraint> filterAcceptedConstraints(List<AvailabilityConstraint> constraints) {
        return constraints.stream()
                .filter(c -> c.getConfidence() >= confidenceThreshold)
                .filter(c -> {
                    boolean hasDays = c.getDays() != null && !c.getDays().isEmpty();
                    boolean hasIntervals = c.getIntervals() != null && !c.getIntervals().isEmpty();
                    return hasDays || hasIntervals;
                })
                .toList();
    }

    private Flux<TeacherAvailability> createAvailabilityRecords(OptionDTO option, AvailabilityConstraint constraint) {

        boolean hasDays = constraint.getDays() != null && !constraint.getDays().isEmpty();
        boolean hasIntervals = constraint.getIntervals() != null && !constraint.getIntervals().isEmpty();

        if (!hasDays && !hasIntervals) {
            return Flux.empty();
        }

        Flux<TeacherAvailability> dayConstraints = Flux.empty();

        if (hasDays) {
            dayConstraints = Flux.fromIterable(constraint.getDays())
                    .flatMap(dayName -> dayService.getDayId(dayName)
                            .onErrorResume(IllegalArgumentException.class, error -> {
                                log.warn("Skipping unsupported day '{}' for option {}", dayName, option.getId());
                                return Mono.empty();
                            }))
                    .flatMap(dayId -> {
                        if (hasIntervals) {
                            return Flux.fromIterable(constraint.getIntervals())
                                    .flatMap(interval -> expandIntervalToTimeslots(option, interval))
                                    .map(timeslotId -> buildAvailability(option, dayId, timeslotId, constraint));
                        }

                        return timeslotService.getAllTimeslots()
                                .map(timeslotId -> buildAvailability(option, dayId, timeslotId, constraint));
                    });
        }

        Flux<TeacherAvailability> timeConstraints = Flux.empty();

        if (hasIntervals && !hasDays) {
            timeConstraints = Flux.fromIterable(constraint.getIntervals())
                    .flatMap(interval -> expandIntervalToTimeslots(option, interval))
                    .flatMap(timeslotId ->
                            dayService.getAllDays()
                                    .flatMapMany(map -> Flux.fromIterable(map.values()))
                                    .map(dayId -> buildAvailability(option, dayId, timeslotId, constraint))
                    );
        }

        return Flux.concat(dayConstraints, timeConstraints);
    }

    private Flux<UUID> expandIntervalToTimeslots(OptionDTO option, uvt.orar.dto.TimeslotDTO interval) {
        return timeslotService.resolveEndTimeOrSlotEnd(interval.getStartHour(), interval.getEndHour())
                .flatMapMany(resolvedEnd ->
                        timeslotService.getTimeslotsInRange(interval.getStartHour(), resolvedEnd)
                )
                .onErrorResume(error -> {
                    log.warn("Skipping invalid interval '{}' - '{}' for option {}",
                            interval.getStartHour(), interval.getEndHour(), option.getId(), error);
                    return Flux.empty();
                });
    }

    private String buildAvailabilityKey(TeacherAvailability row) {
        return row.getTeacherId() + "_" + row.getDayId() + "_" + row.getTimeslotId();
    }

    private TeacherAvailability buildAvailability(
            OptionDTO option,
            UUID dayId,
            UUID timeslotId,
            AvailabilityConstraint constraint) {

        return TeacherAvailability.builder()
                .domainId(option.getDomainId())
                .semesterId(option.getSemesterId())
                .teacherId(option.getTeacher().getId())
                .optionId(option.getId())
                .dayId(dayId)
                .timeslotId(timeslotId)
                .availability(constraint.getAvailability())
                .reason(constraint.getReason())
                .weight(constraint.getConfidence())
                .createdAt(LocalDateTime.now())
                .build();
    }

    private TeacherAvailability chooseStrongerConstraint(
            TeacherAvailability a,
            TeacherAvailability b) {

        int priorityA = availabilityPriority(a.getAvailability());
        int priorityB = availabilityPriority(b.getAvailability());

        if (priorityA > priorityB) {
            return a;
        }

        if (priorityB > priorityA) {
            return b;
        }

        return a.getWeight() >= b.getWeight() ? a : b;
    }

    private int availabilityPriority(int availability) {
        return switch (availability) {
            case -1 -> 4;  // NOT available (strongest)
            case 2 -> 3;   // ONLY available
            case 1 -> 2;   // preferred
            case 0 -> 1;   // neutral
            default -> 0;
        };
    }

    private ExtractionMetric buildMetrics(
            OptionDTO option,
            OllamaExtractionResult result,
            int extractedConstraintCount,
            int acceptedConstraintCount,
            int savedRowCount,
            boolean success,
            String errorMessage,
            long startedAtNanos
    ) {
        return ExtractionMetric.builder()
                .id(UUID.randomUUID())
                .optionId(option.getId())
                .teacherId(option.getTeacher() != null ? option.getTeacher().getId() : null)
                .domainId(option.getDomainId())
                .semesterId(option.getSemesterId())
                .modelName(result != null ? result.getModelName() : ollamaClientService.getConfiguredModel())
                .promptChars(result != null ? result.getPromptChars() : 0)
                .rawResponseChars(result != null ? result.getRawResponseChars() : 0)
                .promptEvalCount(result != null ? result.getPromptEvalCount() : null)
                .evalCount(result != null ? result.getEvalCount() : null)
                .ollamaTotalDurationMs(result != null ? result.getOllamaTotalDurationMs() : null)
                .ollamaLoadDurationMs(result != null ? result.getOllamaLoadDurationMs() : null)
                .processingDurationMs((System.nanoTime() - startedAtNanos) / 1_000_000L)
                .extractedConstraintCount(extractedConstraintCount)
                .acceptedConstraintCount(acceptedConstraintCount)
                .savedRowCount(savedRowCount)
                .confidenceThreshold(confidenceThreshold)
                .jsonValid(result != null && Boolean.TRUE.equals(result.getJsonValid()))
                .emptyOutput(result == null || Boolean.TRUE.equals(result.getEmptyOutput()))
                .success(success && (result == null || Boolean.TRUE.equals(result.getSuccess())))
                .errorMessage(errorMessage != null ? errorMessage : (result != null ? result.getErrorMessage() : null))
                .createdAt(LocalDateTime.now())
                .version(0)
                .build();
    }
}
