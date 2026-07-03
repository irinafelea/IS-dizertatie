package uvt.orar.external_services;

import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;
import uvt.orar.clients.DayClient;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class DayService {

    private final DayClient dayClient;
    private Map<String, UUID> dayMapping = Map.of();

    @PostConstruct
    public void init() {
        loadDays();
    }

    private void loadDays() {
        List<DayClient.DayDTO> days = dayClient.fetchDays().block();
        if (days == null || days.isEmpty()) {
            throw new IllegalStateException("No days returned by external API.");
        }

        Map<String, UUID> loadedMapping = new HashMap<>();

        for (DayClient.DayDTO day : days) {
            if (day.getId() == null || day.getName() == null || day.getName().isBlank()) {
                log.warn("Skipping invalid day payload: {}", day);
                continue;
            }

            String normalizedName = day.getName().toLowerCase();
            loadedMapping.put(normalizedName, day.getId());

            switch (normalizedName) {
                case "monday" -> {
                    loadedMapping.put("Monday", day.getId());
                    loadedMapping.put("luni", day.getId());
                    loadedMapping.put("lunea", day.getId());
                }
                case "tuesday" -> {
                    loadedMapping.put("Tuesday", day.getId());
                    loadedMapping.put("marți", day.getId());
                    loadedMapping.put("marti", day.getId());
                    loadedMapping.put("marțea", day.getId());
                    loadedMapping.put("martea", day.getId());
                }
                case "wednesday" -> {
                    loadedMapping.put("Wednesday", day.getId());
                    loadedMapping.put("miercuri", day.getId());
                    loadedMapping.put("miercurea", day.getId());
                }
                case "thursday" -> {
                    loadedMapping.put("Thursday", day.getId());
                    loadedMapping.put("joi", day.getId());
                    loadedMapping.put("joia", day.getId());
                }
                case "friday" -> {
                    loadedMapping.put("Friday", day.getId());
                    loadedMapping.put("vineri", day.getId());
                    loadedMapping.put("vinerea", day.getId());
                }
            }
        }

        if (loadedMapping.isEmpty()) {
            throw new IllegalStateException("No valid days available after loading external API data.");
        }

        dayMapping = loadedMapping;
        log.info("Loaded {} day aliases from external API", dayMapping.size());
    }

    public Mono<UUID> getDayId(String dayName) {
        UUID dayId = dayMapping.get(dayName);
        if (dayId == null) {
            dayId = dayMapping.entrySet().stream()
                    .filter(entry -> entry.getKey().equalsIgnoreCase(dayName))
                    .map(Map.Entry::getValue)
                    .findFirst()
                    .orElse(null);
        }

        if (dayId == null) {
            return Mono.error(new IllegalArgumentException("Invalid day name: " + dayName));
        }
        return Mono.just(dayId);
    }

    public Mono<Map<String, UUID>> getAllDays() {
        return Mono.just(dayMapping);
    }

    public Mono<Map<UUID, String>> getCanonicalDayNames() {
        Map<UUID, String> canonical = new HashMap<>();

        dayMapping.forEach((name, id) -> {
            switch (name) {
                case "Monday" -> canonical.put(id, "Monday");
                case "Tuesday" -> canonical.put(id, "Tuesday");
                case "Wednesday" -> canonical.put(id, "Wednesday");
                case "Thursday" -> canonical.put(id, "Thursday");
                case "Friday" -> canonical.put(id, "Friday");
                default -> {
                }
            }
        });

        return Mono.just(canonical);
    }
}
