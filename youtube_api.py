# -*- coding: utf-8 -*-
"""
Life Builder Assistant -- busca de videos reais via YouTube Data API v3.

Mesmo principio dos outros servicos externos (ai.py, email_sender.py,
billing.py): sem YOUTUBE_API_KEY configurada o app funciona igual, so
continua mostrando os canais curados/verificados de data.py em vez de videos
especificos.

Por que existe: antes so dava pra oferecer link de canal, porque IDs de video
sao strings aleatorias impossiveis de verificar sem API -- chutar um levaria
o usuario a um video errado ou removido. Com a API a gente pega o video real,
com titulo e thumbnail de verdade.

Cota: a YouTube Data API da 10.000 unidades/dia e cada `search.list` custa
100 -- ou seja ~100 buscas por dia no total, para TODOS os usuarios. Por isso
o resultado e sempre cacheado no banco (tabela youtube_cache, ver init_db em
app.py) e a busca roda em background, nunca no caminho da requisicao.
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
TIMEOUT_SECONDS = 12

# quantos dias um resultado em cache continua valendo. Video pode ser removido
# ou ficar privado; renovar de vez em quando evita link morto sem estourar cota.
CACHE_TTL_DAYS = 30


def youtube_available():
    return bool(YOUTUBE_API_KEY)


def search_video(query, prefer_channel_id=None):
    """Busca o video mais relevante para `query` e devolve
    {"video_id", "titulo", "canal", "thumbnail", "url"}, ou None se a API nao
    estiver configurada / a chamada falhar / nao houver resultado.

    `prefer_channel_id`: se informado, restringe a busca a esse canal. Usado
    para aproveitar a curadoria que ja existe -- em vez de pegar qualquer
    video do YouTube sobre o tema, pega o melhor video DENTRO de um canal que
    ja foi verificado a mao (ver os CANAL_* em data.py).
    """
    if not YOUTUBE_API_KEY or not query:
        return None

    params = {
        "key": YOUTUBE_API_KEY,
        "q": query,
        "part": "snippet",
        "type": "video",
        "maxResults": "1",
        "relevanceLanguage": "pt",
        "regionCode": "BR",
        "safeSearch": "moderate",
        # videos "embutiveis" e de duracao media/longa tendem a ser aula de
        # verdade, nao Short -- que nao serve como recurso de estudo.
        "videoEmbeddable": "true",
    }
    if prefer_channel_id:
        params["channelId"] = prefer_channel_id

    url = f"{YOUTUBE_SEARCH_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "LifeBuilder/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            detalhe = e.read().decode("utf-8")[:200]
        except Exception:
            detalhe = ""
        # 403 costuma ser cota estourada no dia; nesse caso o app segue com os
        # canais curados ate a cota virar.
        print(f"[youtube] HTTP {e.code}: {detalhe}")
        return None
    except (urllib.error.URLError, ValueError, TimeoutError) as e:
        print(f"[youtube] falha na busca {query!r}: {e!r}")
        return None

    items = data.get("items") or []
    if not items:
        return None
    item = items[0]
    video_id = (item.get("id") or {}).get("videoId")
    snippet = item.get("snippet") or {}
    if not video_id:
        return None

    thumbs = snippet.get("thumbnails") or {}
    thumb = (thumbs.get("medium") or thumbs.get("high") or thumbs.get("default") or {}).get("url")
    return {
        "video_id": video_id,
        "titulo": snippet.get("title") or query,
        "canal": snippet.get("channelTitle") or "",
        "thumbnail": thumb or f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",
        "url": f"https://www.youtube.com/watch?v={video_id}",
    }
