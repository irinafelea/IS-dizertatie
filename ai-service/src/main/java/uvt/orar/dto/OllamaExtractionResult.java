package uvt.orar.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import uvt.orar.model.AvailabilityConstraint;

import java.util.ArrayList;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class OllamaExtractionResult {

    @Builder.Default
    private List<AvailabilityConstraint> constraints = new ArrayList<>();

    private String modelName;
    private Integer promptChars;
    private Integer rawResponseChars;
    private Integer promptEvalCount;
    private Integer evalCount;
    private Long ollamaTotalDurationMs;
    private Long ollamaLoadDurationMs;
    private Boolean jsonValid;
    private Boolean emptyOutput;
    private Boolean success;
    private String errorMessage;
}
