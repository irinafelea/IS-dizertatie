package uvt.orar.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;

@Data
@ConfigurationProperties(prefix = "app.external")
public class ExternalApiProperties {
    private String baseUrl;
    private String token;
    private String domainId;
}
