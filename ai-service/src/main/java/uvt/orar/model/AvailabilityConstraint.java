package uvt.orar.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import uvt.orar.dto.TimeslotDTO;

import java.util.ArrayList;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AvailabilityConstraint {

    @Builder.Default
    private List<String> days = new ArrayList<>();

    @Builder.Default
    private List<TimeslotDTO> intervals = new ArrayList<>();

    private Short availability;

    @Builder.Default
    private String reason = "";

    @Builder.Default
    private Double confidence = 0.7;
}
