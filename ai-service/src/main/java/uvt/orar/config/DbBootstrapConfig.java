package uvt.orar.config;

import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.io.ClassPathResource;
import org.springframework.r2dbc.core.DatabaseClient;
import org.springframework.util.StreamUtils;
import reactor.core.publisher.Mono;

import java.nio.charset.StandardCharsets;

@Configuration
public class DbBootstrapConfig {

    @Bean
    ApplicationRunner bootstrapSchema(DatabaseClient db) {
        return args -> {
            String sql = StreamUtils.copyToString(
                    new ClassPathResource("schema.sql").getInputStream(),
                    StandardCharsets.UTF_8
            );

            String[] statements = sql.split(";\\s*\\n");

            Mono<Void> chain = Mono.empty();
            for (String stmt : statements) {
                String s = stmt.trim();
                if (s.isEmpty()) continue;
                chain = chain.then(db.sql(s).then());
            }

            chain.block();
        };
    }
}