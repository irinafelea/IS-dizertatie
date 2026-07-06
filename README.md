# Generarea orarelor universitare folosind un algoritm genetic și căutare adaptivă în vecinătăți extinse

Acest repository conține codul sursă aferent aplicației dezvoltate pentru generarea orarelor universitare și exemple ilustrative ale modului de funcționare. Soluția propusă extinde o platformă existentă de administrare a orarelor prin integrarea a două componente principale:

- un modul bazat pe modele lingvistice mari (LLM), utilizat pentru procesarea opțiunilor cadrelor didactice formulate în limbaj natural;
- un modul de generare automată a orarelor universitare, bazat pe o abordare hibridă care combină un algoritm genetic cu Large Neighborhood Search.


## Descrierea proiectului
Aplicația are ca scop sprijinirea procesului de realizare a orarelor universitare, folosind date instituționale reale, constrângeri hard și soft, disponibilități ale cadrelor didactice și mecanisme de optimizare.

Modulul bazat pe LLM transformă textele introduse de cadrele didactice în constrângeri structurate, care pot fi utilizate ulterior de algoritmul de generare a orarului. Pentru această componentă au fost evaluate mai multe modele rulate local prin Ollama.

Modulul de generare a orarului utilizează o metodă hibridă GA + LNS. Algoritmul genetic construiește o soluție inițială, iar etapa LNS îmbunătățește soluția prin mutări iterative de tip distrugere-reparare. În cadrul acestui modul sunt utilizați algoritmi metaeuristici de optimizare, precum Genetic Algorithm, Large Neighborhood Search, Simulated Annealing și selecția adaptivă bazată pe mecanismul Upper Confidence Bound pentru alegerea operatorilor.

## Conținutul directorului

Directorul conține codul sursă al componentelor dezvoltate în cadrul lucrării. Acesta este organizat în trei directoare principale:

```text
is-dizertatie
├── ai-service/
|   ├── src/
|   │   ├── main/
|   │   │   ├── java/
|   │   │   │   └── uvt/orar/
|   │   │   │       ├── clients/
|   │   │   │       ├── config/
|   │   │   │       ├── controller/
|   │   │   │       ├── dto/
|   │   │   │       ├── external_services/
|   │   │   │       ├── model/
|   │   │   │       ├── ollama/
|   │   │   │       ├── repository/
|   │   │   │       └── service/
|   │   │   └── resources/
|   │   │       ├── application.yml
|   │   │       └── schema.sql
|   │   └── test/
|   ├── pom.xml
|   └── .env.example
|
├── demo/
│   ├── distrugere-reparare.gif
│   ├── evolutia-solutiei-ga-lns.gif
│   └── maparea-optiunilor.gif
|
└── generator-service/
    ├── app/
    │   ├── routers/
    │   ├── models/
    │   ├── entities/
    │   ├── services/
    │   ├── external_services/
    │   ├── mappers/
    │   ├── utils/
    │   ├── db.py
    │   └── main.py
    ├── algorithm/
    │   ├── algorithm_classes/
    │   ├── algorithm_helpers/
    │   ├── algorithm_score/
    │   ├── genetic_algorithm/
    │   ├── hard_constraints/
    │   ├── large_neighbourhood_search/
    │   ├── matrix_classes/
    │   ├── simulated_annealing/
    │   ├── soft_constraints/
    │   └── timetable_algorithm.py
    ├── alembic/
    ├── config/
    ├── constants/
    ├── helpers/
    ├── printers/
    ├── results/
    ├── requirements.txt
    ├── alembic.ini
    └── .env.example
```

- `ai-service/` – conține serviciul bazat pe modele lingvistice mari, utilizat pentru procesarea opțiunilor cadrelor didactice formulate în limbaj natural și transformarea acestora în constrângeri structurate;

- `generator-service/` – conține serviciul responsabil de generarea automată a orarelor universitare, folosind abordarea hibridă bazată pe algoritm genetic și Large Neighborhood Search;

- `demo/` – conține exemple ilustrative ale modului de funcționare a celor două module.


## Tehnologii utilizate

| Tehnologie | Versiune / observații |
|---|---|
| Java | 21 |
| Spring Boot | 3.4.2 |
| Maven | 4.0.0/ utilizat pentru `ai-service` |
| Python | 3.13 |
| pip | 25.3 |
| FastAPI | utilizat pentru `generator-service` |
| Uvicorn | utilizat pentru rularea serviciului FastAPI |
| PostgreSQL | utilizat pentru persistența datelor |
| R2DBC PostgreSQL | utilizat în `ai-service` pentru acces reactiv la baza de date |
| SQLAlchemy | utilizat în `generator-service` |
| Redis | utilizat pentru cache în platforma principală |
| Kafka | utilizat pentru comunicarea asincronă în platforma principală |
| Docker | utilizat pentru rularea serviciilor și a infrastructurii auxiliare |
| Ollama | utilizat pentru rularea locală a modelelor LLM |
| Modele LLM locale | `llama3.1:8b`, `mistral`, `gemma3:4b`, `gemma3:12b` |


## Demo

### Maparea opțiunilor cadrelor didactice

În această demonstrație, două opțiuni formulate în limbaj natural sunt transformate în reprezentări structurate și mapate pe intervalele orare utilizate de platformă.

![Demo](demo/maparea-optiunilor.gif)

### Evoluția soluției: GA → LNS

Pornind de la soluția inițială generată de algoritmul genetic, exemplul evidențiază îmbunătățirile succesive obținute în etapa mecanismului Large Neighborhood Search.

![Demo](demo/evolutia-solutiei-ga-lns.gif)


### Ciclu distrugere–reparare în LNS

Acest exemplu prezintă un pas al mecanismului LNS, în care o parte a soluției este eliminată printr-un operator de distrugere, iar apoi este reconstruită printr-un operator de reparare.

![Demo](demo/distrugere-reparare.gif)


## Prezentare video

Videoclipul prezintă funcționalitățile dezvoltate în cadrul lucrării, arhitectura platformei existente, cele două module adăugate și fluxul complet al aplicației. De asemenea, sunt prezentate rezultatele obținute pentru cele două componente.

https://github.com/user-attachments/assets/fab596b2-bd36-4545-9c7d-4b1648edc531