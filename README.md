
# LPS e‑Commerce 2025 (v4.1 corrigido)
- **Status:** http://localhost:8080/status
- **UI (storefront demo):** http://localhost:8080/storefront
- **Seletor de Features:** http://localhost:8080/config

## Rodar
```bash
docker compose up --build
```

## Derivar produto pelas features
1) Gere `features.yaml` em `/config` (cole e salve na raiz).
2) Rode:
```bash
docker run --rm -v "$PWD":/work -w /work python:3.11-alpine python derive_product.py features.yaml
docker compose -f docker-compose.yml -f docker-compose.override.yml up -d --build
```
