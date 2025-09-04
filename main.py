from fastapi import FastAPI
from pydantic import BaseModel
import tldextract

app = FastAPI()

# Modelo de entrada
class ContentCheck(BaseModel):
    text: str

# Lista de palavras e sites adultos
BLACKLIST = [
    # Palavras ofensivas e relacionadas a sexo
    "sexo", "pornografia", "nudez", "xxx", "putaria",
    "caralho", "porra", "fuder", "buceta", "boquete",
    "transar", "puta", "merda", "corno", "vagabunda", "vadia", "prostituta", "vagabundo"
    

    # Domínios/sítios adultos comuns
    "xvideos", "pornhub", "redtube", "xnxx", "brazzers",
    "onlyfans", "xhamster", "cam4", "youporn", "bangbros",
    "hentai", "erotico", "camgirls"
]

def check_blacklist(text: str):
    """Verifica se o texto contém palavras ou sites da blacklist."""
    text_lower = text.lower()

    # Checa palavras proibidas
    blocked_words = [word for word in BLACKLIST if word in text_lower]

    # Se for um link/URL, checa o domínio
    extracted = tldextract.extract(text_lower)
    domain = extracted.domain  # ex: 'xvideos' de 'www.xvideos.com'
    if domain in BLACKLIST:
        blocked_words.append(domain)

    return blocked_words

@app.post("/check-content/")
def check_content(data: ContentCheck):
    blocked_words = check_blacklist(data.text)

    if blocked_words:
        return {
            "allowed": False,
            "reason": "Conteúdo bloqueado",
            "blocked_words": list(set(blocked_words))  # sem duplicatas
        }
    return {
        "allowed": True,
        "reason": "Conteúdo permitido"
    }

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import re

app = FastAPI(title="API de Controle Parental Avançada")

# Modelos de dados
class ScheduleItem(BaseModel):
    day: str  # Ex: "segunda-feira"
    start_hour: str  # "07:00"
    end_hour: str    # "21:00"
    allowed: bool

class Permissions(BaseModel):
    admin_override: bool
    temporary_access: bool

class Restrictions(BaseModel):
    max_daily_usage: str  # Ex: "4h"
    block_unapproved_sites: bool

class ParentalControlSettings(BaseModel):
    blocked_categories: List[str]
    blocked_keywords: List[str]  # Palavras-chave em URLs
    blocked_domains: List[str]   # Domínios proibidos
    allowed_categories: List[str]
    schedule: List[ScheduleItem]
    permissions: Permissions
    restrictions: Restrictions

# Configurações iniciais
settings = ParentalControlSettings(
    blocked_categories=["pornografia", "conteudo_adulto", "drogas"],
    blocked_keywords=["sex", "porn", "drugs", "adult"],
    blocked_domains=["exampleporn.com", "drugsales.com"],
    allowed_categories=["educacao", "entretenimento_infantil", "noticias_gerais"],
    schedule=[
        ScheduleItem(day="segunda-feira", start_hour="07:00", end_hour="21:00", allowed=True),
        ScheduleItem(day="sabado", start_hour="09:00", end_hour="23:00", allowed=True),
        ScheduleItem(day="domingo", start_hour="09:00", end_hour="21:00", allowed=True)
    ],
    permissions=Permissions(admin_override=True, temporary_access=True),
    restrictions=Restrictions(max_daily_usage="4h", block_unapproved_sites=True)
)

# Verifica horário permitido
def is_time_allowed(day: str, time: str) -> bool:
    schedule_item = next((s for s in settings.schedule if s.day.lower() == day.lower()), None)
    if not schedule_item:
        return False

    current_hour, current_minute = map(int, time.split(":"))
    start_hour, start_minute = map(int, schedule_item.start_hour.split(":"))
    end_hour, end_minute = map(int, schedule_item.end_hour.split(":"))

    after_start = current_hour > start_hour or (current_hour == start_hour and current_minute >= start_minute)
    before_end = current_hour < end_hour or (current_hour == end_hour and current_minute <= end_minute)

    return schedule_item.allowed and after_start and before_end

# Verifica URL
def is_url_allowed(url: str) -> bool:
    url_lower = url.lower()
    # Domínios proibidos
    for domain in settings.blocked_domains:
        if domain.lower() in url_lower:
            return False
    # Palavras-chave
    for keyword in settings.blocked_keywords:
        if re.search(rf"\b{re.escape(keyword)}\b", url_lower):
            return False
    return True

# Endpoint de verificação de acesso
@app.get("/verificar_acesso")
def verificar_acesso(categoria: str = None, url: str = None, dia: str = None, horario: str = None):
    if dia is None or horario is None:
        raise HTTPException(status_code=400, detail="Dia e horário são obrigatórios")

    # Checa horário
    if not is_time_allowed(dia, horario):
        return {"acesso": "bloqueado", "motivo": "fora do horário permitido"}

    # Checa categoria
    if categoria and categoria.lower() in [c.lower() for c in settings.blocked_categories]:
        return {"acesso": "bloqueado", "motivo": f"categoria '{categoria}' proibida"}

    # Checa URL
    if url and not is_url_allowed(url):
        return {"acesso": "bloqueado", "motivo": f"url '{url}' proibida"}

    return {"acesso": "permitido"}

# Endpoint para atualizar configurações
@app.post("/atualizar_config")
def atualizar_config(novas_config: ParentalControlSettings):
    global settings
    settings = novas_config
    return {"status": "Configurações atualizadas com sucesso!"}
