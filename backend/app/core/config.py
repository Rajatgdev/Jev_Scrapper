"""Central config. Reads .env. Thresholds and the topic sentence are policy —
they live here, never inside the model."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # scraper
    firecrawl_api_key: str = ""

    # jev
    jev_api_key: str = ""
    jev_model: str = "jev-latest"

    # openai
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # thresholds
    severity_conf_min: float = 0.60
    relevant_prob_min: float = 0.60
    noise_prob_max: float = 0.70



    # email (Resend)
    send_email: bool = False
    resend_api_key: str = ""
    digest_from: str = ""
    digest_to: str = ""

    # cors
    allowed_origins: str = "http://localhost:5173"

    # db (off by default)
    use_db: bool = False
    database_url: str = ""

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
