package uvt.orar.clients;

import lombok.Data;
import lombok.RequiredArgsConstructor;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;
import uvt.orar.config.ExternalApiProperties;

import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class DayClient {

    private final WebClient webClient;
    private final ExternalApiProperties properties;

    public Mono<List<DayDTO>> fetchDays() {
        return request("/days")
                .retrieve()
                .bodyToMono(new ParameterizedTypeReference<List<DayDTO>>() {});
    }

    public Mono<DayDTO> fetchDayById(UUID id) {
        return request("/days/" + id)
                .retrieve()
                .bodyToMono(DayDTO.class);
    }

    private WebClient.RequestHeadersSpec<?> request(String path) {
        String url = buildUrl(path);

        WebClient.RequestHeadersSpec<?> request = webClient.get()
                .uri(url)
                .header(HttpHeaders.ACCEPT, MediaType.APPLICATION_JSON_VALUE);

        if (properties.getToken() != null && !properties.getToken().isBlank()) {
            request = request.header(HttpHeaders.AUTHORIZATION, "Bearer " + properties.getToken());
        }

        return request;
    }

    private String buildUrl(String path) {
        String baseUrl = properties.getBaseUrl();
        if (baseUrl == null || baseUrl.isBlank() || baseUrl.contains("${")) {
            throw new IllegalStateException(
                    "app.external.base-url is not configured. Set it in application.yml or the environment."
            );
        }

        return baseUrl.replaceAll("/$", "") + path;
    }

    @Data
    public static class DayDTO {
        private UUID id;
        private String name;
    }
}
