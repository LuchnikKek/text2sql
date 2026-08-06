from fastapi import APIRouter, HTTPException

from app.enrichment import EnrichmentError, EntityNotFound, get_source, source_names
from app.schemas import EnrichResponse

router = APIRouter(tags=["enrichment"])


@router.get("/enrich/{source}/{entity_id}", response_model=EnrichResponse)
async def enrich(source: str, entity_id: str) -> EnrichResponse:
    enrichment_source = get_source(source)
    if enrichment_source is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown enrichment source: {source}. Known: {source_names()}",
        )

    try:
        data = await enrichment_source.fetch(entity_id)
    except EntityNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except EnrichmentError as exc:
        # Источник недоступен/ответил мусором — это проблема внешней системы
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return EnrichResponse(source=source, entity_id=entity_id, data=data)
