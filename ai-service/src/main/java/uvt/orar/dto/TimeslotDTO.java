package uvt.orar.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.UUID;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TimeslotDTO {
    private UUID id;
    private String startHour; // "08:00"
    private String endHour;   // "10:00"
}
