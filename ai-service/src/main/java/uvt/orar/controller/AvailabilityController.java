package uvt.orar.controller;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;
import uvt.orar.dto.AvailabilityDTO;
import uvt.orar.dto.OptionDTO;
import uvt.orar.dto.ProcessingResultDTO;
import uvt.orar.service.AvailabilityProcessingService;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

@Slf4j
@RestController
@RequestMapping("/api/v1/availability")
@RequiredArgsConstructor
public class AvailabilityController {

    private final AvailabilityProcessingService processingService;

    @GetMapping(value = "/{optionId}", produces = MediaType.APPLICATION_JSON_VALUE)
    public Flux<AvailabilityDTO> getAvailabilityByOptionId(
            @PathVariable("optionId") UUID optionId
    ) {
        return processingService.getByOptionId(optionId);
    }

    @GetMapping(produces = MediaType.APPLICATION_JSON_VALUE)
    public Flux<AvailabilityDTO> getAllAvailability() {
        return processingService.getAll();
    }

    @GetMapping(value = "/{semesterId}/{domainId}", produces = MediaType.APPLICATION_JSON_VALUE)
    public Flux<AvailabilityDTO> getBySemesterIdAndDomainId(@PathVariable("semesterId") UUID semesterId,
                                                            @PathVariable("domainId") UUID domainId) {
        return processingService.getBySemesterIdAndDomainId(semesterId, domainId);
    }

    @PostMapping("/extract")
    public Mono<ResponseEntity<Map<String, Object>>> extractAndSave(@Valid @RequestBody OptionDTO option) {
        return processingService.processTeacherOption(option)
                .map(result -> buildExtractResponse(option, result))
                .onErrorResume(e -> {
                    log.error("Error extracting and saving constraints", e);
                    Map<String, Object> error = new HashMap<>();
                    error.put("error", e.getMessage());
                    return Mono.just(ResponseEntity.internalServerError().body(error));
                });
    }

    private ResponseEntity<Map<String, Object>> buildExtractResponse(OptionDTO option, ProcessingResultDTO result) {
        Map<String, Object> response = new HashMap<>();
        response.put("teacherName",
                option.getTeacher().getFirstName() + " " + option.getTeacher().getLastName());
        response.put("extractedConstraints", result.getExtractedConstraints());
        response.put("constraintCount", result.getExtractedConstraints().size());
        response.put("savedRowsCount", result.getSavedRows().size());
        response.put("savedRows", result.getSavedRows());
        response.put("metrics", result.getMetrics());
        response.put("benchmark", result.getBenchmark());
        return ResponseEntity.ok(response);
    }
}
