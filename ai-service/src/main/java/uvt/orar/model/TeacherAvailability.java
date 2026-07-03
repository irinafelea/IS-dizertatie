package uvt.orar.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.Id;
import org.springframework.data.annotation.Version;
import org.springframework.data.relational.core.mapping.Column;
import org.springframework.data.relational.core.mapping.Table;

import java.time.LocalDateTime;
import java.util.UUID;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Table("teacher_availability")
public class TeacherAvailability {
    @Id
    private UUID id;

    @Column("domain_id")
    private UUID domainId;

    @Column("semester_id")
    private UUID semesterId;

    @Column("teacher_id")
    private UUID teacherId;

    @Column("option_id")
    private UUID optionId;

    @Column("day_id")
    private UUID dayId;

    @Column("timeslot_id")
    private UUID timeslotId;

    @Column("availability")
    private int availability;

    @Column("reason")
    private String reason;

    @Column("weight")
    private double weight;

    @Column("created_at")
    private LocalDateTime createdAt;

    @Version
    private Integer version;
}
