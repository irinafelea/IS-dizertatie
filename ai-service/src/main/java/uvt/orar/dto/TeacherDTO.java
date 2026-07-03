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
public class TeacherDTO {
    private UUID id;
    private String title;
    private String firstName;
    private String lastName;
    private String email;
    private String phone;
}
