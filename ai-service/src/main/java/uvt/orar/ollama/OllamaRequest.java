package uvt.orar.ollama;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class OllamaRequest {
    private String model;
    private String prompt;
    private boolean stream;
    private String format;

    @JsonProperty("options")
    private OllamaOptions options;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class OllamaOptions {
        private double temperature;

        @JsonProperty("num_predict")
        private int numPredict;

        @JsonProperty("top_p")
        private double topP;

        @JsonProperty("top_k")
        private int topK;
    }
}
