package uvt.orar.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import uvt.orar.model.AvailabilityConstraint;
import uvt.orar.model.ExtractionMetric;
import uvt.orar.service.BenchmarkEvaluationService.BenchmarkExportResult;

import java.util.ArrayList;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ProcessingResultDTO {

    @Builder.Default
    private List<AvailabilityConstraint> extractedConstraints = new ArrayList<>();

    @Builder.Default
    private List<AvailabilityDTO> savedRows = new ArrayList<>();

    private ExtractionMetric metrics;

    private BenchmarkExportResult benchmark;
}
