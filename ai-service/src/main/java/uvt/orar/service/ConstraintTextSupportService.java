package uvt.orar.service;

import org.springframework.stereotype.Service;
import uvt.orar.dto.TimeslotDTO;
import uvt.orar.model.AvailabilityConstraint;

import java.text.Normalizer;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Service
public class ConstraintTextSupportService {

    private static final List<String> WEEKDAY_ORDER = List.of(
            "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"
    );

    private static final Map<String, String> RO_TO_EN_DAY = Map.ofEntries(
            Map.entry("luni", "Monday"),
            Map.entry("lunea", "Monday"),
            Map.entry("marti", "Tuesday"),
            Map.entry("marți", "Tuesday"),
            Map.entry("martea", "Tuesday"),
            Map.entry("marțea", "Tuesday"),
            Map.entry("miercuri", "Wednesday"),
            Map.entry("miercurea", "Wednesday"),
            Map.entry("joi", "Thursday"),
            Map.entry("joia", "Thursday"),
            Map.entry("vineri", "Friday"),
            Map.entry("vinerea", "Friday")
    );

    private static final Pattern DAY_RANGE_PATTERN = Pattern.compile(
            "\\b(de\\s+)?(luni|lunea|marti|marți|martea|marțea|miercuri|miercurea|joi|joia|vineri|vinerea)\\b" +
                    "\\s*(?:-|pana|până)\\s*" +
                    "\\b(marti|marți|martea|marțea|miercuri|miercurea|joi|joia|vineri|vinerea|luni|lunea)\\b",
            Pattern.CASE_INSENSITIVE | Pattern.UNICODE_CASE
    );
    private static final Pattern SINGLE_DAY_PATTERN = Pattern.compile(
            "\\b(luni|lunea|marti|marți|martea|marțea|miercuri|miercurea|joi|joia|vineri|vinerea)\\b",
            Pattern.CASE_INSENSITIVE | Pattern.UNICODE_CASE
    );
    private static final Pattern DIRECT_INTERVAL_PATTERN = Pattern.compile(
            "(?<!\\d)(\\d{1,2}:\\d{2})\\s*[-–]\\s*(\\d{1,2}:\\d{2})(?!\\d)"
    );
    private static final Pattern BETWEEN_INTERVAL_PATTERN = Pattern.compile(
            "\\b(?:intre|între)\\s+(\\d{1,2}:\\d{2})\\s+(?:si|și)\\s+(\\d{1,2}:\\d{2})\\b",
            Pattern.CASE_INSENSITIVE | Pattern.UNICODE_CASE
    );
    private static final Pattern FROM_TO_INTERVAL_PATTERN = Pattern.compile(
            "\\bde\\s+la\\s+(\\d{1,2}:\\d{2})\\s+(?:pana\\s+la|până\\s+la)\\s+(\\d{1,2}:\\d{2})\\b",
            Pattern.CASE_INSENSITIVE | Pattern.UNICODE_CASE
    );
    private static final Pattern AFTER_TIME_PATTERN = Pattern.compile(
            "\\b(?:dupa|după|incepand\\s+cu|începând\\s+cu|de\\s+la|cel\\s+mai\\s+devreme\\s+de\\s+la)\\s+(\\d{1,2}:\\d{2})\\b",
            Pattern.CASE_INSENSITIVE | Pattern.UNICODE_CASE
    );
    private static final Pattern STANDALONE_TIME_PATTERN = Pattern.compile(
            "(?<!\\d)(\\d{1,2}:\\d{2})(?!\\d)"
    );

    public List<String> extractDaysFromText(String text) {
        if (text == null || text.isBlank()) {
            return new ArrayList<>();
        }

        String lower = text.toLowerCase(Locale.ROOT);
        LinkedHashSet<String> result = new LinkedHashSet<>();

        Matcher rangeMatcher = DAY_RANGE_PATTERN.matcher(lower);
        while (rangeMatcher.find()) {
            String enStart = RO_TO_EN_DAY.get(rangeMatcher.group(2));
            String enEnd = RO_TO_EN_DAY.get(rangeMatcher.group(3));
            if (enStart != null && enEnd != null) {
                result.addAll(expandDayRange(enStart, enEnd));
            }
        }

        String withoutRanges = DAY_RANGE_PATTERN.matcher(lower).replaceAll(" ");
        Matcher singleMatcher = SINGLE_DAY_PATTERN.matcher(withoutRanges);
        while (singleMatcher.find()) {
            String enDay = RO_TO_EN_DAY.get(singleMatcher.group(1));
            if (enDay != null) {
                result.add(enDay);
            }
        }

        return new ArrayList<>(result);
    }

    public List<TimeslotDTO> extractIntervalsFromText(String text) {
        if (text == null || text.isBlank()) {
            return List.of();
        }

        LinkedHashMap<String, TimeslotDTO> intervals = new LinkedHashMap<>();
        String remaining = text;

        collectIntervals(DIRECT_INTERVAL_PATTERN.matcher(remaining), intervals, true);
        remaining = DIRECT_INTERVAL_PATTERN.matcher(remaining).replaceAll(" ");

        collectIntervals(BETWEEN_INTERVAL_PATTERN.matcher(remaining), intervals, true);
        remaining = BETWEEN_INTERVAL_PATTERN.matcher(remaining).replaceAll(" ");

        collectIntervals(FROM_TO_INTERVAL_PATTERN.matcher(remaining), intervals, true);
        remaining = FROM_TO_INTERVAL_PATTERN.matcher(remaining).replaceAll(" ");

        Matcher afterMatcher = AFTER_TIME_PATTERN.matcher(remaining);
        while (afterMatcher.find()) {
            String start = normalizeTime(afterMatcher.group(1));
            addInterval(intervals, start, "23:59");
        }
        remaining = AFTER_TIME_PATTERN.matcher(remaining).replaceAll(" ");

        Matcher timeMatcher = STANDALONE_TIME_PATTERN.matcher(remaining);
        while (timeMatcher.find()) {
            addInterval(intervals, normalizeTime(timeMatcher.group(1)), null);
        }

        return new ArrayList<>(intervals.values());
    }

    public String resolveSourceLine(
            AvailabilityConstraint constraint,
            List<String> sourceLines,
            int constraintIndex,
            int constraintCount
    ) {
        if (sourceLines == null || sourceLines.isEmpty()) {
            return "";
        }

        if (sourceLines.size() == constraintCount && constraintIndex >= 0 && constraintIndex < sourceLines.size()) {
            return sourceLines.get(constraintIndex);
        }

        return findBestSourceLine(constraint, sourceLines);
    }

    public String findBestSourceLine(AvailabilityConstraint constraint, List<String> sourceLines) {
        if (sourceLines == null || sourceLines.isEmpty()) {
            return "";
        }

        String reason = constraint.getReason() == null ? "" : normalizeText(constraint.getReason());
        List<String> intervalTokens = new ArrayList<>();
        if (constraint.getIntervals() != null) {
            constraint.getIntervals().forEach(interval -> {
                if (interval.getStartHour() != null) {
                    intervalTokens.add(interval.getStartHour());
                }
                if (interval.getEndHour() != null) {
                    intervalTokens.add(interval.getEndHour());
                }
            });
        }

        String bestLine = sourceLines.getFirst();
        int bestScore = Integer.MIN_VALUE;

        for (String line : sourceLines) {
            String normalizedLine = normalizeText(line);
            int score = 0;

            if (!reason.isBlank() && normalizedLine.contains(reason)) {
                score += 20;
            }

            for (String token : intervalTokens) {
                if (normalizedLine.contains(normalizeText(token))) {
                    score += 3;
                }
            }

            List<String> lineDays = extractDaysFromText(line);
            if (constraint.getDays() != null) {
                for (String day : constraint.getDays()) {
                    if (lineDays.contains(day)) {
                        score += 2;
                    }
                }
            }

            if (score > bestScore) {
                bestScore = score;
                bestLine = line;
            }
        }

        return bestLine;
    }

    private void collectIntervals(Matcher matcher, Map<String, TimeslotDTO> intervals, boolean consumeEndTime) {
        while (matcher.find()) {
            String start = normalizeTime(matcher.group(1));
            String end = consumeEndTime ? normalizeTime(matcher.group(2)) : null;
            addInterval(intervals, start, end);
        }
    }

    private void addInterval(Map<String, TimeslotDTO> intervals, String start, String end) {
        if (start == null || start.isBlank()) {
            return;
        }

        String key = start + "->" + (end == null ? "" : end);
        intervals.putIfAbsent(key, TimeslotDTO.builder()
                .startHour(start)
                .endHour(end)
                .build());
    }

    private String normalizeTime(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }

        String[] parts = value.trim().split(":");
        if (parts.length != 2) {
            return value.trim();
        }

        int hour = Integer.parseInt(parts[0]);
        int minute = Integer.parseInt(parts[1]);
        return String.format("%02d:%02d", hour, minute);
    }

    private List<String> expandDayRange(String startDay, String endDay) {
        int startIdx = WEEKDAY_ORDER.indexOf(startDay);
        int endIdx = WEEKDAY_ORDER.indexOf(endDay);

        if (startIdx == -1 || endIdx == -1) {
            return List.of();
        }

        if (startIdx <= endIdx) {
            return new ArrayList<>(WEEKDAY_ORDER.subList(startIdx, endIdx + 1));
        }

        List<String> wrapped = new ArrayList<>(WEEKDAY_ORDER.subList(startIdx, WEEKDAY_ORDER.size()));
        wrapped.addAll(WEEKDAY_ORDER.subList(0, endIdx + 1));
        return wrapped;
    }

    private String normalizeText(String value) {
        String normalized = Normalizer.normalize(value, Normalizer.Form.NFD);
        return normalized.replaceAll("\\p{M}+", "").toLowerCase(Locale.ROOT);
    }
}
