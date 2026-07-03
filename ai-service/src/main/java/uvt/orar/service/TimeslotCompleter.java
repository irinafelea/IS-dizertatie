package uvt.orar.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;
import uvt.orar.external_services.TimeslotService;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Slf4j
@Service
@RequiredArgsConstructor
public class TimeslotCompleter {

    private final TimeslotService timeslotService;

    private static final Pattern START_TIME_ONLY = Pattern.compile(
            "(?:de la|la ora|ora)\\s+(\\d{1,2}):(\\d{2})|" +
                    "(?:luni|lunea|mar[tț]i|mar[tț]ea|miercuri|miercurea|joi|joia|vineri|vinerea)\\s+(\\d{1,2}):(\\d{2})",
            Pattern.CASE_INSENSITIVE
    );

    private static final Pattern AFTER_KEYWORD = Pattern.compile(
            "(?:dupa|după)(?:\\s+in\\s+\\d+)?",
            Pattern.CASE_INSENSITIVE
    );

    // Pattern for explicit count
    private static final Pattern EXPLICIT_COUNT = Pattern.compile(
            "(\\d+)\\s*(?:laboratoare|module|ore|cursuri|seminare)|" +  // Plural + number
                    "cate\\s+(\\d+)\\s*(?:module|ore|laboratoare|cursuri)|" +
                    "cele\\s+(\\d+)\\s*(?:laboratoare|module|ore|cursuri)",
            Pattern.CASE_INSENSITIVE
    );

    // Pattern for singular activities (always 1 module)
    private static final Pattern SINGULAR_ACTIVITY = Pattern.compile(
            "\\b(curs|laborator|seminar|proiect)\\b(?!e)",  // Singular only (not "cursuri", "laboratoare")
            Pattern.CASE_INSENSITIVE
    );

    public Mono<String> completeIntervals(String line) {

        Matcher afterMatcher = AFTER_KEYWORD.matcher(line);
        if (afterMatcher.find()) {
            return completeSequentialActivity(line);
        }

        // Find all start times in the line
        Matcher startMatcher = START_TIME_ONLY.matcher(line);
        List<TimeMatch> timeMatches = new ArrayList<>();

        while (startMatcher.find()) {
            String startHour = startMatcher.group(1) != null ? startMatcher.group(1) : startMatcher.group(3);
            String startMin = startMatcher.group(2) != null ? startMatcher.group(2) : startMatcher.group(4);

            if (startHour != null && startMin != null) {
                timeMatches.add(new TimeMatch(
                        startMatcher.start(),
                        startMatcher.end(),
                        startHour,
                        startMin
                ));
            }
        }

        if (timeMatches.isEmpty()) {
            return Mono.just(line);
        }

        // Process each time match and build completed line
        return completeAllTimeMatches(line, timeMatches);
    }

    /**
     * Complete all time matches in a line
     */
    private Mono<String> completeAllTimeMatches(String line, List<TimeMatch> timeMatches) {

        // Infer module count once for the whole line
        Integer modules = inferModuleCount(line);

        if (modules == null) {
            log.debug("Cannot infer module count for line (plural without count or no activity): {}", line);
            return Mono.just(line);
        }

        // Build list of completion tasks
        List<Mono<TimeCompletion>> completionTasks = new ArrayList<>();

        for (TimeMatch match : timeMatches) {
            // Check if this time already has an interval (HH:MM-HH:MM)
            if (hasIntervalAtPosition(line, match.end)) {
                continue;
            }

            String startTime = formatTime(
                    Integer.parseInt(match.startHour),
                    Integer.parseInt(match.startMin)
            );

            Mono<TimeCompletion> task = calculateEndTimeFromSlots(startTime, modules)
                    .map(endTime -> new TimeCompletion(
                            match.start,
                            match.end,
                            match.startHour + ":" + match.startMin,
                            startTime + "-" + endTime
                    ));

            completionTasks.add(task);
        }

        if (completionTasks.isEmpty()) {
            return Mono.just(line);
        }

        // Execute all completion tasks and rebuild the line
        return Mono.zip(completionTasks, completions -> {

            // Sort by position (descending) to replace from end to start
            List<TimeCompletion> sorted = new ArrayList<>();
            for (Object obj : completions) {
                sorted.add((TimeCompletion) obj);
            }
            sorted.sort((a, b) -> Integer.compare(b.start, a.start));

            StringBuilder result = new StringBuilder(line);

            for (TimeCompletion completion : sorted) {
                // Find the exact position again (in case indices shifted)
                int pos = result.indexOf(completion.original, Math.max(0, completion.start - 5));
                if (pos != -1) {
                    result.replace(pos, pos + completion.original.length(), completion.completed);

                    log.debug("Replaced '{}' with '{}' at position {}",
                            completion.original, completion.completed, pos);
                }
            }

            log.debug("Completed all intervals: '{}' -> '{}'", line, result.toString());

            return result.toString();
        });
    }

    /**
     * Check if there's already an interval at this position (HH:MM-HH:MM)
     */
    private boolean hasIntervalAtPosition(String line, int position) {
        if (position >= line.length()) return false;

        String remaining = line.substring(position);
        Pattern intervalContinuation = Pattern.compile("^\\s*-\\s*\\d{1,2}:\\d{2}");

        return intervalContinuation.matcher(remaining).find();
    }

    private static class TimeMatch {
        int start;
        int end;
        String startHour;
        String startMin;

        TimeMatch(int start, int end, String startHour, String startMin) {
            this.start = start;
            this.end = end;
            this.startHour = startHour;
            this.startMin = startMin;
        }
    }

    private static class TimeCompletion {
        int start;
        int end;
        String original;
        String completed;

        TimeCompletion(int start, int end, String original, String completed) {
            this.start = start;
            this.end = end;
            this.original = original;
            this.completed = completed;
        }
    }

    private Mono<String> completeSequentialActivity(String line) {

        Pattern previousInterval = Pattern.compile("(\\d{1,2}):(\\d{2})-(\\d{1,2}):(\\d{2})");

        Matcher m = previousInterval.matcher(line);
        String lastEndTime = null;

        while (m.find()) {
            lastEndTime = formatTime(
                    Integer.parseInt(m.group(3)),
                    Integer.parseInt(m.group(4))
            );
        }

        if (lastEndTime == null) {
            log.warn("No previous interval found for 'dupa' in: {}", line);
            return Mono.just(line);
        }

        return findNextSlotStart(lastEndTime)
                .flatMap(nextStartTime -> {

                    if (nextStartTime == null) {
                        return Mono.just(line);
                    }

                    String afterPart = line.substring(line.toLowerCase().indexOf("dupa"));
                    Integer modules = inferModuleCount(afterPart);

                    if (modules == null) {
                        log.debug("Cannot infer modules for 'dupa', using 1");
                        modules = 1;  // Default singular "laborator" = 1
                    }

                    return calculateEndTimeFromSlots(nextStartTime, modules)
                            .map(endTime -> {

                                if (endTime == null) {
                                    return line;
                                }

                                String replacement = "dupa " + nextStartTime + "-" + endTime;

                                return line.replaceFirst(
                                        "(?i)dupa(?:\\s+in\\s+\\d+)?",
                                        replacement
                                );
                            });
                });
    }

    private Mono<String> findNextSlotStart(String endTime) {

        return timeslotService.getAll()
                .collectList()
                .map(timeslots -> {

                    String normalizedEndTime = normalizeTime(endTime);

                    for (int i = 0; i < timeslots.size() - 1; i++) {
                        String slotEnd = normalizeTime(timeslots.get(i).getEndHour());

                        if (slotEnd.equals(normalizedEndTime)) {
                            return normalizeTime(timeslots.get(i + 1).getStartHour());
                        }
                    }

                    return null;
                });
    }

    private Mono<String> calculateEndTimeFromSlots(String startTime, int modules) {
        return timeslotService.getAll()
                .collectList()
                .map(timeslots -> {

                    String normalizedStart = normalizeTime(startTime);
                    int startSlotIndex = -1;

                    for (int i = 0; i < timeslots.size(); i++) {
                        String slotStart = normalizeTime(timeslots.get(i).getStartHour());

                        if (slotStart.equals(normalizedStart)) {
                            startSlotIndex = i;
                            break;
                        }
                    }

                    if (startSlotIndex == -1) {
                        log.warn("Start time {} not found in timeslots", startTime);
                        return null;
                    }

                    int endSlotIndex = startSlotIndex + modules - 1;

                    if (endSlotIndex >= timeslots.size()) {
                        log.warn("End slot index {} exceeds available slots ({}), capping",
                                endSlotIndex, timeslots.size() - 1);
                        endSlotIndex = timeslots.size() - 1;
                    }

                    String endTime = normalizeTime(timeslots.get(endSlotIndex).getEndHour());

                    log.debug("Slots: start={} (index={}), modules={}, end={} (index={})",
                            normalizedStart, startSlotIndex, modules, endTime, endSlotIndex);

                    return endTime;
                });
    }

    /**
     * Infer number of modules from context
     * Returns null if cannot be inferred (plural without explicit count)
     */
    private Integer inferModuleCount(String line) {
        String lower = line.toLowerCase();

        // PRIORITY 1: Explicit count (REQUIRED for plural forms)
        Matcher explicitMatcher = EXPLICIT_COUNT.matcher(line);
        if (explicitMatcher.find()) {
            // Group 1: "2 laboratoare", "3 module", "4 cursuri"
            String count = explicitMatcher.group(1);
            if (count != null) {
                int modules = Integer.parseInt(count);
                log.debug("Found explicit count: {} modules", modules);
                return Math.min(modules, 8);
            }

            // Group 2: "cate 3 module"
            count = explicitMatcher.group(2);
            if (count != null) {
                int modules = Integer.parseInt(count);
                log.debug("Found explicit count (cate): {} modules", modules);
                return Math.min(modules, 8);
            }

            // Group 3: "cele 2 laboratoare"
            count = explicitMatcher.group(3);
            if (count != null) {
                int modules = Integer.parseInt(count);
                log.debug("Found explicit count (cele): {} modules", modules);
                return Math.min(modules, 8);
            }
        }

        // PRIORITY 2: Check for plural without count 
        if (lower.contains("cursuri") ||
                lower.contains("laboratoare") ||
                lower.contains("seminare")) {
            log.debug("Found plural form without explicit count - cannot infer");
            return null;  // Plural requires explicit count
        }

        // PRIORITY 3: Singular activities 
        Matcher singularMatcher = SINGULAR_ACTIVITY.matcher(line);
        if (singularMatcher.find()) {
            String activity = singularMatcher.group(1).toLowerCase();
            log.debug("Found singular '{}' -> 1 module", activity);
            return 1;  // All singular activities = 1 module
        }

        // PRIORITY 4: Already has complete interval
        if (hasCompleteInterval(line)) {
            return null;
        }

        // PRIORITY 5: Cannot infer
        log.debug("Cannot infer module count from: {}", line);
        return null;
    }

    private boolean hasCompleteInterval(String line) {
        Pattern completeInterval = Pattern.compile("\\d{1,2}:\\d{2}\\s*[-–]\\s*\\d{1,2}:\\d{2}");
        return completeInterval.matcher(line).find();
    }

    private String normalizeTime(String time) {
        if (time == null) return null;

        time = time.trim().replace('.', ':');

        String[] parts = time.split(":");
        if (parts.length != 2) {
            log.warn("Invalid time format: {}", time);
            return time;
        }

        try {
            int hour = Integer.parseInt(parts[0]);
            int minute = Integer.parseInt(parts[1]);
            return String.format("%02d:%02d", hour, minute);
        } catch (NumberFormatException e) {
            log.warn("Cannot parse time: {}", time);
            return time;
        }
    }

    private String formatTime(int hour, int minute) {
        return String.format("%02d:%02d", hour, minute);
    }
}
