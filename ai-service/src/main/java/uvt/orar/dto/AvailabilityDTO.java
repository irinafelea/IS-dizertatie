package uvt.orar.dto;

import java.util.UUID;

public record AvailabilityDTO(
        UUID teacherId,
        UUID dayId,
        UUID timeslotId,
        int availability,
        String reason,
        Double weight
) {}
