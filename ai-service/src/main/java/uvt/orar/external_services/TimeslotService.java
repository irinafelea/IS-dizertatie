package uvt.orar.external_services;

import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;
import uvt.orar.clients.TimeslotClient;
import uvt.orar.config.ExternalApiProperties;
import uvt.orar.dto.TimeslotDTO;

import java.time.LocalTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Objects;
import java.util.UUID;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class TimeslotService {
    @Autowired
    private final ExternalApiProperties properties;

    private final TimeslotClient timeslotClient;

    private List<TimeslotDTO> timeslots = List.of();

    private static final DateTimeFormatter FLEXIBLE_TIME_FORMATTER =
            DateTimeFormatter.ofPattern("H:mm");

    @PostConstruct
    public void init() {
        loadTimeslots();
    }

    private void loadTimeslots() {
        UUID domainId = UUID.fromString(properties.getDomainId());

        List<TimeslotDTO> loaded = timeslotClient.fetchTimeslots(domainId);
        if (loaded == null || loaded.isEmpty()) {
            throw new IllegalStateException("No timeslots returned by external API.");
        }

        List<TimeslotDTO> valid = loaded.stream()
                .filter(Objects::nonNull)
                .filter(ts -> {
                    boolean ok = true;

                    if (ts.getId() == null) {
                        log.error("Invalid timeslot: missing id: {}", ts);
                        ok = false;
                    }
                    if (ts.getStartHour() == null || ts.getStartHour().isBlank()) {
                        log.error("Invalid timeslot: missing startTime for id={}: {}", ts.getId(), ts);
                        ok = false;
                    }
                    if (ts.getEndHour() == null || ts.getEndHour().isBlank()) {
                        log.error("Invalid timeslot: missing endTime for id={}: {}", ts.getId(), ts);
                        ok = false;
                    }

                    if (ok) {
                        try {
                            LocalTime.parse(ts.getStartHour());
                            LocalTime.parse(ts.getEndHour());
                        } catch (Exception e) {
                            log.error("Invalid timeslot: cannot parse start/end for id={}: start={}, end={}",
                                    ts.getId(), ts.getStartHour(), ts.getEndHour(), e);
                            ok = false;
                        }
                    }

                    return ok;
                })
                .toList();

        if (valid.isEmpty()) {
            throw new IllegalStateException("No valid timeslots available after loading external API data.");
        }

        timeslots = valid.stream()
                .sorted(Comparator.comparing(ts -> LocalTime.parse(ts.getStartHour())))
                .toList();

        log.info("Loaded {} valid timeslots from external API", timeslots.size());
    }

    public Flux<UUID> getTimeslotsInRange(String startTime, String endTime) {
        if (startTime == null || endTime == null || startTime.isBlank() || endTime.isBlank()) {
            return Flux.empty();
        }

        if (!startTime.contains(":")) startTime = startTime.concat(":00");
        if (!endTime.contains(":")) endTime = endTime.concat(":59");

        if (endTime.contains("24")) endTime = "23:59";

        try {
            LocalTime start = LocalTime.parse(startTime, FLEXIBLE_TIME_FORMATTER);
            LocalTime end = LocalTime.parse(endTime, FLEXIBLE_TIME_FORMATTER);

            if (!end.isAfter(start)) {
                log.warn("Invalid range (end <= start): {} - {}", startTime, endTime);
                return Flux.empty();
            }

            List<UUID> matchingSlots = timeslots.stream()
                    .filter(slot -> {
                        LocalTime slotStart = LocalTime.parse(slot.getStartHour());
                        LocalTime slotEnd = LocalTime.parse(slot.getEndHour());
                        return slotStart.isBefore(end) && slotEnd.isAfter(start);
                    })
                    .map(TimeslotDTO::getId)
                    .toList();

            return Flux.fromIterable(matchingSlots);

        } catch (Exception e) {
            log.error("Error parsing time range: {} - {}", startTime, endTime, e);
            return Flux.error(e);
        }
    }

    public Mono<TimeslotDTO> getTimeslotByStartTime(String startTime) {
        if (startTime == null || startTime.isBlank()) return Mono.empty();

        return Flux.fromIterable(timeslots)
                .filter(ts -> startTime.equals(ts.getStartHour()))
                .next();
    }

    public Mono<String> resolveEndTimeOrSlotEnd(String startTime, String endTime) {
        if (endTime != null && !endTime.isBlank()) {
            return Mono.just(endTime);
        }
        if (startTime == null || startTime.isBlank()) {
            return Mono.empty();
        }

        return getTimeslotByStartTime(startTime)
                .map(TimeslotDTO::getEndHour)
                .switchIfEmpty(Mono.defer(() -> {
                    log.warn("Cannot infer endTime: no timeslot starts at {}", startTime);
                    return Mono.empty();
                }));
    }

    public Flux<UUID> getAllTimeslots() {
        return Flux.fromIterable(
                timeslots.stream().map(TimeslotDTO::getId).collect(Collectors.toList())
        );
    }

    public Flux<TimeslotDTO> getAll() {
        return Flux.fromIterable(new ArrayList<>(timeslots));
    }
}
