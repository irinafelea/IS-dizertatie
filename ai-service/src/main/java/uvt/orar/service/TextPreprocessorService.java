package uvt.orar.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Slf4j
@Service
public class TextPreprocessorService {

    private final TimeslotCompleter timeslotCompleter;

    private static final Pattern BULLET_POINT = Pattern.compile("^\\s*[-•⁠*]\\s*");

    public TextPreprocessorService(TimeslotCompleter timeslotCompleter) {
        this.timeslotCompleter = timeslotCompleter;
    }

    /**
     * Preprocesses raw Romanian text into normalized constraint lines.
     * Each constraint becomes a separate line starting with "-"
     */
    public Mono<String> preprocess(String restrictions, String information) {
        log.info("Starting text preprocessing");

        List<String> normalizedLines = new ArrayList<>();

        if (restrictions != null && !restrictions.trim().isEmpty() &&
                !restrictions.equalsIgnoreCase("nu e cazul") && !restrictions.equals("-")) {

            if (startsWithDayName(restrictions)) {
                restrictions = "Restrictii \n" + restrictions.toLowerCase();
            }

            normalizedLines.addAll(extractConstraintLines(restrictions));
        }

        normalizedLines.add("\n");

        if (information != null && !information.trim().isEmpty() && !information.equals("-")) {
            normalizedLines.addAll(extractConstraintLines(information));
        }

        return Flux.fromIterable(normalizedLines)
                .filter(line -> !line.trim().isEmpty())
                .filter(line -> !isMetadata(line))
                .flatMap(timeslotCompleter::completeIntervals)
                .map(completed -> "- " + completed.trim())
                .collectList()
                .map(lines -> {
                    String output = String.join("\n", lines).trim();
                    log.info("Preprocessed into {} constraint lines", lines.size());
                    log.info("Preprocessed text:\n{}", output);
                    return output;
                });
    }

    /**
     * Extracts individual constraint lines from a text block
     */
    private List<String> extractConstraintLines(String text) {
        List<String> lines = new ArrayList<>();

        text = normalizeText(text);

        // split by dot or newline
        String[] sentences = text.split("[\\.\\n\\r]+");

        String currentHeader = null;

        for (String sentence : sentences) {
            sentence = sentence.trim();

            if (sentence.isEmpty()) {
                continue;
            }

            if (isHeaderLine(sentence)) {
                currentHeader = sentence.contains(":") ? sentence.replace(":", "") : sentence;
                continue;
            }

            if (isMetadata(sentence)) {
                continue;
            }

            String enrichedSentence = sentence;
            if (currentHeader != null && !currentHeader.isBlank()) {
                enrichedSentence = currentHeader + " " + (sentence.startsWith("- ") ? sentence.replace("- ", "") : sentence);
            }

            if (hasExplicitBullets(enrichedSentence)) {
                lines.addAll(extractBulletPoints(enrichedSentence));
            } else {
                lines.addAll(intelligentSplit(enrichedSentence));
            }
        }

        return lines;
    }

    /**
     * Split a line into multiple constraints
     */
    private List<String> intelligentSplit(String line) {
        List<String> constraints = new ArrayList<>();

        if (isMetadata(line)) {
            return constraints;
        }

        if (line.contains(";")) {
            String[] parts = line.split(";");
            for (String part : parts) {
                part = part.trim();
                if (!part.isEmpty() && !isMetadata(part)) {
                    constraints.add(part);
                }
            }
            return constraints;
        }

        if (hasMultipleSentences(line)) {
            String[] sentences = line.split("(?<=[.!])\\s+(?=[A-ZĂÎÂȘȚ])");
            for (String sentence : sentences) {
                sentence = sentence.trim();
                if (!sentence.isEmpty() && !isMetadata(sentence)) {
                    constraints.add(sentence);
                }
            }
            return constraints;
        }

        constraints.add(line);
        return constraints;
    }

    /**
     * Check if line has multiple sentences
     */
    private boolean hasMultipleSentences(String line) {
        Pattern p = Pattern.compile("[.!]\\s+[A-ZĂÎÂȘȚ]");
        return p.matcher(line).find();
    }

    /**
     * Check if has bullet points
     */
    private boolean hasExplicitBullets(String text) {
        return BULLET_POINT.matcher(text).find();
    }

    /**
     * Extract bullet point lines
     */
    private List<String> extractBulletPoints(String text) {
        List<String> lines = new ArrayList<>();
        String[] rawLines = text.split("\n");

        for (String line : rawLines) {
            Matcher m = BULLET_POINT.matcher(line);
            if (m.find()) {
                String cleaned = m.replaceFirst("").trim();
                if (!cleaned.isEmpty()) {
                    lines.addAll(processBulletLine(cleaned));
                }
            } else if (!line.trim().isEmpty() && !isHeaderLine(line)) {
                lines.addAll(intelligentSplit(line));
            }
        }

        return lines;
    }

    /**
     * Process bullet line with multiple times
     */
    private List<String> processBulletLine(String line) {
        List<String> constraints = new ArrayList<>();

        // Pattern: "day (time1 si time2)"
        Pattern multiTimePattern = Pattern.compile(
                "(luni|lunea|mar[tț]i|mar[tț]ea|miercuri|miercurea|joi|joia|vineri|vinerea)\\s*" +
                        "\\(([^)]+)\\s+si\\s+([^)]+)\\)",
                Pattern.CASE_INSENSITIVE
        );

        Matcher m = multiTimePattern.matcher(line);
        if (m.find()) {
            String day = m.group(1);
            String time1 = m.group(2).trim();
            String time2 = m.group(3).trim();

            constraints.add(day + " (" + time1 + ")");
            constraints.add(day + " (" + time2 + ")");
            return constraints;
        }

        constraints.add(line);
        return constraints;
    }

    /**
     * Check if line is a header
     */
    private boolean isHeaderLine(String line) {
        String lower = line.toLowerCase().trim();
        return lower.equals("restricții") ||
                lower.equals("restrictii") ||
                lower.equals("informații") ||
                lower.equals("informatii") ||
                lower.equals("sunt disponibil") ||
                lower.equals("sunt disponibila") ||
                lower.equals("disponibilitate") ||
                lower.endsWith(":");
    }

    /**
     * Check if text is metadata/commentary (not a constraint)
     */
    private boolean isMetadata(String text) {
        String lower = text.toLowerCase().trim();

        return lower.equals("sau inversate") ||
                lower.equals("mersi") ||
                lower.equals("spor") ||
                lower.startsWith("nu mai stiu") ||
                lower.startsWith("ca si in anii trecuti") ||
                lower.startsWith("alternativ") ||
                lower.startsWith("în rest nu am restricții") ||
                lower.startsWith("in rest nu am restrictii") ||
                lower.startsWith("în rest, nu am restricții") ||
                lower.startsWith("in rest, nu am restrictii") ||
                lower.startsWith("multumesc") ||
                lower.contains("mulțumesc") ||
                lower.contains(" para ") ||
                lower.contains(" impara ") ||
                lower.contains(" pară ") ||
                lower.contains(" impară ") ||
                lower.contains(" pare ") ||
                lower.contains(" impare ") ||
                lower.contains("am mentionat disponibilitatea");
    }

    /**
     * Normalize text
     */
    private String normalizeText(String text) {
        text = text.replace("ţ", "ț").replace("ş", "ș");
        text = text.replace("Ţ", "Ț").replace("Ş", "Ș");
        text = text.replace("⁠", "");
        text = text.replace("•", "-");
        text = text.replace("–", "-").replace("—", "-");

        text = normalizeHourRanges(text);

        text = text.replaceAll("(\\d{1,2})\\.(\\d{2})(?!\\d)", "$1:$2");
        text = convertPmAmTo24h(text);

        return text;
    }

    private String normalizeHourRanges(String text) {
        if (text == null || text.isBlank()) {
            return text;
        }

        Pattern p = Pattern.compile(
                "(?<!\\d)" +
                        "(\\d{1,2})(?::(\\d{2}))?" +
                        "\\s*-\\s*" +
                        "(\\d{1,2})(?::(\\d{2}))?" +
                        "(?!\\d)",
                Pattern.CASE_INSENSITIVE | Pattern.UNICODE_CASE
        );

        Matcher m = p.matcher(text);
        StringBuffer sb = new StringBuffer();

        while (m.find()) {
            String original = m.group(0);

            int startHour = Integer.parseInt(m.group(1));
            String startMinute = m.group(2) != null ? m.group(2) : "00";

            int endHour = Integer.parseInt(m.group(3));
            String endMinute = m.group(4) != null ? m.group(4) : "00";

            if (startHour > 23 || endHour > 23) {
                m.appendReplacement(sb, Matcher.quoteReplacement(original));
                continue;
            }

            int from = m.start();
            int to = m.end();

            String before = text.substring(Math.max(0, from - 25), from).toLowerCase(Locale.ROOT);
            String after = text.substring(to, Math.min(text.length(), to + 25)).toLowerCase(Locale.ROOT);

            boolean explicitTimeFormat =
                    m.group(2) != null || m.group(4) != null;

            boolean looksLikeTimeContext =
                    before.matches(".*\\b(ora|orele|între|intre|de la|după|dupa|până la|pana la|intervalul|interval)\\b.*")
                            || after.matches("^\\s*(am|pm|fix)\\b.*");

            boolean looksLikeNonTimeContext =
                    after.matches("^\\s*(zile|zilei|zi|zilele|ani|an|anul|grupa|grupe|grup|seria|serii|saptamani|săptămâni|ore?)\\b.*")
                            || before.matches(".*\\b(anul|grupa|grupe|seria|serii)\\s*$");

            if (looksLikeNonTimeContext) {
                m.appendReplacement(sb, Matcher.quoteReplacement(original));
                continue;
            }

            if (!explicitTimeFormat && !looksLikeTimeContext) {
                m.appendReplacement(sb, Matcher.quoteReplacement(original));
                continue;
            }

            String replacement = String.format(
                    "%02d:%s-%02d:%s",
                    startHour, startMinute,
                    endHour, endMinute
            );

            m.appendReplacement(sb, Matcher.quoteReplacement(replacement));
        }

        m.appendTail(sb);
        return sb.toString();
    }

    /**
     * Convert PM/AM to 24h
     */
    private String convertPmAmTo24h(String text) {
        Pattern pmPattern = Pattern.compile("(\\d{1,2}):(\\d{2})\\s*PM", Pattern.CASE_INSENSITIVE);
        Matcher m = pmPattern.matcher(text);
        StringBuffer sb = new StringBuffer();

        while (m.find()) {
            int hour = Integer.parseInt(m.group(1));
            String minute = m.group(2);

            if (hour < 12) {
                hour += 12;
            }

            m.appendReplacement(sb, String.format("%02d:%s", hour, minute));
        }
        m.appendTail(sb);

        Pattern pmPattern2 = Pattern.compile("(\\d{1,2})\\s*PM", Pattern.CASE_INSENSITIVE);
        m = pmPattern2.matcher(sb.toString());
        sb = new StringBuffer();

        while (m.find()) {
            int hour = Integer.parseInt(m.group(1));
            if (hour < 12) {
                hour += 12;
            }
            m.appendReplacement(sb, String.format("%02d:00", hour));
        }
        m.appendTail(sb);

        return sb.toString();
    }

    private boolean startsWithDayName(String text) {
        if (text == null || text.isBlank()) {
            return false;
        }

        String lower = text.trim().toLowerCase(Locale.ROOT);

        while (lower.startsWith("-")) {
            lower = lower.substring(1).stripLeading();
        }

        return lower.matches(
                "(?s)^(luni|lunea|mar[tț]i|mar[tț]ea|miercuri|miercurea|joi|joia|vineri|vinerea)\\b.*"
        );
    }
}
