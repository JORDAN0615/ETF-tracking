from app.adapters.base import SourceAdapter
from app.adapters.capital_portfolio import CapitalPortfolioAdapter
from app.adapters.fhtrust_etf_html import FhtrustEtfHtmlAdapter
from app.adapters.nomura_etfweb import NomuraEtfWebAdapter
from app.adapters.tsit_etf_detail import TsitEtfDetailAdapter
from app.adapters.unified_ezmoney import UnifiedEzmoneyAdapter


ADAPTERS: dict[str, SourceAdapter] = {
    "capital_portfolio": CapitalPortfolioAdapter(),
    "fhtrust_etf_html": FhtrustEtfHtmlAdapter(),
    "nomura_etfweb": NomuraEtfWebAdapter(),
    "tsit_etf_detail": TsitEtfDetailAdapter(),
    "unified_ezmoney": UnifiedEzmoneyAdapter(),
}


def get_adapter(source_type: str) -> SourceAdapter:
    try:
        return ADAPTERS[source_type]
    except KeyError as exc:
        raise ValueError(f"Unsupported source type: {source_type}") from exc
