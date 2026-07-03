package uvt.orar.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.UUID;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ExtractionMetric {
    private UUID id;
    private UUID optionId;
    private UUID teacherId;
    private UUID domainId;
    private UUID semesterId;
    private String modelName;
    private Integer promptChars;
    private Integer rawResponseChars;
    private Integer promptEvalCount;
    private Integer evalCount;
    private Long ollamaTotalDurationMs;
    private Long ollamaLoadDurationMs;
    private Long processingDurationMs;
    private Integer extractedConstraintCount;
    private Integer acceptedConstraintCount;
    private Integer savedRowCount;
    private Double confidenceThreshold;
    private Boolean jsonValid;
    private Boolean emptyOutput;
    private Boolean success;
    private String errorMessage;
    private LocalDateTime createdAt;
    private Integer version;
}
