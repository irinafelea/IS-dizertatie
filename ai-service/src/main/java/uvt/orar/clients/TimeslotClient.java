package uvt.orar.clients;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpHeaders;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;
import uvt.orar.config.ExternalApiProperties;
import uvt.orar.dto.TimeslotDTO;

import java.util.List;
import java.util.UUID;

@Service
@Data
@Builder
@AllArgsConstructor
public class TimeslotClient {
    @Autowired
    private final RestClient restClient;
    @Autowired
    private final ExternalApiProperties properties;

    public List<TimeslotDTO> fetchTimeslots(UUID domainId) {
        String baseUrl = properties.getBaseUrl();
        if (baseUrl == null || baseUrl.isBlank() || baseUrl.contains("${")) {
            throw new IllegalStateException(
                    "app.external.base-url is not configured. Set BASE_URL in the environment or .env file."
            );
        }

        String url = baseUrl.replaceAll("/$", "")
                + "/timeslots/bachelor/" + domainId;

        RestClient.RequestHeadersSpec<?> request = restClient.get()
                .uri(url)
                .header(HttpHeaders.ACCEPT, "application/json");

        if (properties.getToken() != null && !properties.getToken().isBlank()) {
            request = request.header(HttpHeaders.AUTHORIZATION, "Bearer " + properties.getToken());
        }

        List<TimeslotDTO> data = request.retrieve()
                .body(new ParameterizedTypeReference<List<TimeslotDTO>>() {});

        if (data == null) {
            throw new IllegalStateException("Expected modules endpoint to return a JSON list.");
        }

        return data;
    }

    public TimeslotDTO fetchTimeslotById(UUID id) {
        String baseUrl = properties.getBaseUrl();
        if (baseUrl == null || baseUrl.isBlank() || baseUrl.contains("${")) {
            throw new IllegalStateException(
                    "app.external.base-url is not configured. Set BASE_URL in the environment or .env file."
            );
        }

        String url = baseUrl.replaceAll("/$", "")
                + "/timeslots/" + id;

        RestClient.RequestHeadersSpec<?> request = restClient.get()
                .uri(url)
                .header(HttpHeaders.ACCEPT, "application/json");

        if (properties.getToken() != null && !properties.getToken().isBlank()) {
            request = request.header(HttpHeaders.AUTHORIZATION, "Bearer " + properties.getToken());
        }

        TimeslotDTO data = request.retrieve()
                .body(new ParameterizedTypeReference<TimeslotDTO>() {});

        if (data == null) {
            throw new IllegalStateException("Expected modules endpoint to return a JSON list.");
        }

        return data;
    }
}
