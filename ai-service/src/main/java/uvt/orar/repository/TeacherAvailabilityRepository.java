package uvt.orar.repository;

import org.springframework.data.r2dbc.repository.Query;
import org.springframework.data.r2dbc.repository.R2dbcRepository;
import org.springframework.stereotype.Repository;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;
import uvt.orar.model.TeacherAvailability;

import java.util.UUID;

@Repository
public interface TeacherAvailabilityRepository extends R2dbcRepository<TeacherAvailability, UUID> {

    Flux<TeacherAvailability> findByOptionId(UUID optionId);

    @Query("SELECT * FROM teacher_availability WHERE semester_id = :semesterId AND domain_id = :domainId")
    Flux<TeacherAvailability> getBySemesterIdAndDomainId(UUID semesterId, UUID domainId);

    Mono<TeacherAvailability> save(TeacherAvailability teacherAvailability);

    @Query("DELETE FROM teacher_availability WHERE option_id = :optionId")
    Mono<Integer> deleteByOptionId(UUID optionId);
}