import datetime
import json
import httpx
import os
import urllib.parse
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import database

load_dotenv()
database.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Paffloat")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

SESSION_FILE = "data/session.json"
STEAM_OPENID_URL = "https://steamcommunity.com/openid/login"

TYPE_MAPPING = {
    "CSGO_Type_Knife": "armes",
    "CSGO_Type_Hands": "gants",
    "Type_CustomPlayer": "agents",
    "CSGO_Type_WeaponCase": "caisses",
    "CSGO_Tool_Sticker": "stickers",
    "CSGO_Tool_Keychain": "porte-cles",
    "CSGO_Tool_Patch": "ecussons",
    "CSGO_Type_Collectible": "pins",
    "CSGO_Type_MusicKit": "kits_musique"
}

STACKABLE_TYPES = {
    "CSGO_Type_WeaponCase", "CSGO_Tool_Sticker", "CSGO_Tool_Keychain", 
    "CSGO_Tool_Patch", "CSGO_Type_Collectible"
}

def get_db():
    with database.SessionLocal() as db:
        yield db

def load_state() -> dict[str, Optional[str]]:
    """Charge la session depuis le fichier s'il existe."""
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Erreur de lecture de la session: {e}")
    return {"steam_id": None, "pseudo": None, "avatar": None}

def save_state():
    """Sauvegarde l'état actuel dans le fichier."""
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)

state = load_state()

def get_float_category(float_value: Optional[float]) -> str:
    if float_value is None: return "N/A"
    if float_value < 0.07: return "FN"
    if float_value < 0.15: return "MW"
    if float_value < 0.38: return "FT"
    if float_value < 0.45: return "WW"
    return "BS"

def get_item_type(tags: list) -> str:
    for tag in tags:
        cat = tag.get("category")
        int_name = tag.get("internal_name")
        if cat == "Weapon" or int_name == "CSGO_Type_Knife":
            return "armes"
        if int_name in TYPE_MAPPING:
            return TYPE_MAPPING[int_name]
    return "autre"

def extract_steam_xml_data(text: str, tag: str, default: str) -> str:
    """Extrait rapidement une valeur d'un profil XML Steam."""
    start_tag = f"<{tag}><![CDATA["
    end_tag = f"]]></{tag}>"
    start = text.find(start_tag)
    if start != -1:
        start += len(start_tag)
        end = text.find(end_tag, start)
        if end != -1:
            return text[start:end]
    return default

async def get_steam_profile(steam_id: str):
    url = f"https://steamcommunity.com/profiles/{steam_id}/?xml=1"
    pseudo = steam_id
    avatar = "https://avatars.steamstatic.com/fef49e7fa7e1997310d705b2a6158ff8dc1cdfeb_full.jpg"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=5.0)
            if response.status_code == 200:
                pseudo = extract_steam_xml_data(response.text, "steamID", pseudo)
                avatar = extract_steam_xml_data(response.text, "avatarFull", avatar)
    except Exception as e:
        print(f"Erreur lors de la récupération du profil Steam: {e}")
    
    return pseudo, avatar

async def get_live_exchange_rate(db: Session) -> float:
    endpoint = "currency_usd_eur"
    now = datetime.datetime.utcnow()
    cache = db.query(database.APICache).filter(database.APICache.endpoint == endpoint).first()

    if cache and (now - cache.last_called).total_seconds() < 43200:
        return float(cache.response_data) 

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.frankfurter.dev/v1/latest?base=USD&symbols=EUR", timeout=5.0)
            if response.status_code == 200:
                rate = response.json()["rates"]["EUR"]
                if cache:
                    cache.last_called = now 
                    cache.response_data = str(rate) 
                else:
                    db.add(database.APICache(endpoint=endpoint, last_called=now, response_data=str(rate)))
                db.commit()
                return rate
    except Exception as e:
        print(f"Erreur API taux de change: {e}")

    return float(cache.response_data) if cache else 0.87 

async def fetch_inventory(steam_id: str, db: Session, force_refresh: bool = False):
    endpoint = f"steam_inv_{steam_id}"
    now = datetime.datetime.utcnow()
    cache = db.query(database.APICache).filter(database.APICache.endpoint == endpoint).first()

    if not force_refresh and cache and (now - cache.last_called).total_seconds() < 900 and cache.response_data: 
        items = json.loads(cache.response_data) 
        saved_prices = {s.asset_id: s.purchase_price for s in db.query(database.Skin).filter(database.Skin.steam_id == steam_id).all()}
        for item in items:
            asset_id = item.get("asset_id")
            if asset_id in saved_prices:
                item["purchase_price"] = saved_prices[asset_id]
        return items

    url = f"https://steamcommunity.com/inventory/{steam_id}/730/2?l=fenglish&count=50"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            if response.status_code == 403:
                print(f"Inventaire privé ou accès refusé pour {steam_id}")
                return []
            response.raise_for_status()
            data = response.json()
            
            if "descriptions" not in data or "assets" not in data:
                return json.loads(cache.response_data) if cache and cache.response_data else [] 

            saved_skins = db.query(database.Skin).filter(database.Skin.steam_id == steam_id).all()
            db_skins_map = {s.asset_id: s for s in saved_skins}
            desc_map = {f"{d['classid']}_{d['instanceid']}": d for d in data["descriptions"]}

            asset_props_map = {}
            for prop_group in data.get("asset_properties", []):
                asset_id = str(prop_group.get("assetid"))
                props = {p.get("propertyid"): p for p in prop_group.get("asset_properties", [])}
                f_val = float(props[2]["float_value"]) if 2 in props else None
                s_val = props[1]["int_value"] if 1 in props else None
                asset_props_map[asset_id] = {"float": f_val, "seed": s_val}

            items = []
            stackables_map = {}

            for asset in data["assets"]:
                desc_key = f"{asset['classid']}_{asset['instanceid']}"
                desc = desc_map.get(desc_key, {})
                
                if desc.get("marketable") != 1: 
                    continue
                    
                asset_id = str(asset["assetid"])
                raw_name = desc.get("name", "Objet inconnu")
                clean_name = raw_name.split(" (")[0]
                tags = desc.get("tags", [])
                item_type = get_item_type(tags)

                rarity_color = "2c2c2c"
                for tag in tags:
                    if tag.get("category") == "Rarity":
                        internal_name = tag.get("internal_name", "")
                        if "Common" in internal_name: 
                            rarity_color = "B0C3D9"
                        elif "Uncommon" in internal_name: 
                            rarity_color = "5E98D9"
                        elif "Rare" in internal_name: 
                            rarity_color = "4B69FF"
                        elif "Mythical" in internal_name: 
                            rarity_color = "8847FF"
                        elif "Legendary" in internal_name: 
                            rarity_color = "D32CE6"
                        elif "Ancient" in internal_name: 
                            rarity_color = "EB4B4B"
                        elif "Contraband" in internal_name: 
                            rarity_color = "E4AE33"
                        else: 
                            rarity_color = tag.get("color", "2c2c2c")
                        break

                if "★" in raw_name:
                    rarity_color = "FFD700"
                is_stackable = any(tag.get("internal_name") in STACKABLE_TYPES for tag in tags)
                img_url = f"https://community.cloudflare.steamstatic.com/economy/image/{desc.get('icon_url')}"

                if is_stackable:
                    if clean_name in stackables_map:
                        stackables_map[clean_name]["count"] += 1
                        if stackables_map[clean_name]["purchase_price"] == 0.00 and asset_id in db_skins_map:
                            old_skin = db_skins_map[asset_id] 
                            stackables_map[clean_name].update({
                                "purchase_price": old_skin.purchase_price,
                                "batches": old_skin.batches
                            })
                            if clean_name not in db_skins_map:
                                new_skin = database.Skin(steam_id=steam_id, asset_id=clean_name, name=clean_name, purchase_price=old_skin.purchase_price, batches=old_skin.batches)
                                db.add(new_skin)
                                db_skins_map[clean_name] = new_skin
                    else:
                        source_skin = db_skins_map.get(clean_name) or db_skins_map.get(asset_id) 
                        price = source_skin.purchase_price if source_skin else 0.00
                        batches_str = getattr(source_skin, "batches", None) if source_skin else None
                        
                        if source_skin and clean_name not in db_skins_map:
                            new_skin = database.Skin(steam_id=steam_id, asset_id=clean_name, name=clean_name, purchase_price=price, batches=batches_str)
                            db.add(new_skin)
                            db_skins_map[clean_name] = new_skin

                        stackables_map[clean_name] = {
                            "asset_id": clean_name, "name": clean_name, "image_url": img_url,
                            "is_stackable": True, "count": 1, "purchase_price": price, "batches": batches_str,
                            "rarity_color": rarity_color, "item_type": item_type 
                        }
                else:
                    db_skin = db_skins_map.get(asset_id) 
                    market_hash_name = desc.get("market_hash_name", raw_name)
                    
                    item = {
                        "asset_id": asset_id, "name": clean_name, "market_hash_name": market_hash_name,
                        "image_url": img_url, "float_value": "N/A", "float_category": "N/A", "seed": "N/A",
                        "purchase_price": db_skin.purchase_price if db_skin else 0.00,
                        "is_stackable": False, "rarity_color": rarity_color, "item_type": item_type
                    }

                    if db_skin and db_skin.float_value is not None:
                        item.update({
                            "float_value": db_skin.float_value,
                            "float_category": db_skin.float_category or get_float_category(db_skin.float_value), 
                            "seed": db_skin.seed if db_skin.seed is not None else "N/A"
                        })
                    elif asset_id in asset_props_map:
                        f_val = asset_props_map[asset_id]["float"]
                        s_val = asset_props_map[asset_id]["seed"]
                        if f_val is not None:
                            f_cat = get_float_category(f_val)
                            item.update({"float_value": f_val, "float_category": f_cat, "seed": s_val if s_val is not None else "N/A"})
                            if not db_skin:
                                db.add(database.Skin(steam_id=steam_id, asset_id=asset_id, name=clean_name, float_value=f_val, float_category=f_cat, seed=s_val, purchase_price=0.0))
                            else:
                                db_skin.float_value, db_skin.float_category, db_skin.seed = f_val, f_cat, s_val 

                    items.append(item)

            items.extend(stackables_map.values())

            cache_data = json.dumps(items)
            if cache:
                cache.last_called, cache.response_data = now, cache_data 
            else:
                db.add(database.APICache(endpoint=endpoint, last_called=now, response_data=cache_data))
            db.commit()
            return items
            
    except Exception as e:
        print(f"Erreur API Steam: {e}")
        return json.loads(cache.response_data) if cache and cache.response_data else [] 

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, db: Session = Depends(get_db)):
    rate = await get_live_exchange_rate(db)
    return templates.TemplateResponse(request=request, name="index.html", context={
        "steam_id": state["steam_id"], 
        "pseudo": state["pseudo"], 
        "avatar": state.get("avatar"),
        "usd_to_eur": rate
    })

@app.get("/login")
async def login_redirect(request: Request):
    """Redirige l'utilisateur vers la page de connexion Steam."""
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.url.netloc)
    realm = f"{scheme}://{host}"
    return_to = f"{realm}/auth/steam/callback"

    params = {
        "openid.ns": "http://specs.openid.net/auth/2.0",
        "openid.mode": "checkid_setup",
        "openid.return_to": return_to,
        "openid.realm": realm,
        "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
        "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
    }
    
    url = f"{STEAM_OPENID_URL}?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url)

@app.get("/auth/steam/callback")
async def steam_callback(request: Request):
    """Vérifie la réponse de Steam et connecte l'utilisateur."""
    params = dict(request.query_params)
    params["openid.mode"] = "check_authentication"

    async with httpx.AsyncClient() as client:
        response = await client.post(STEAM_OPENID_URL, data=params)

    if "is_valid:true" in response.text:
        claimed_id = params.get("openid.claimed_id", "")
        steam_id = claimed_id.split("/")[-1]

        pseudo, avatar = await get_steam_profile(steam_id)
        state.update({"steam_id": steam_id, "pseudo": pseudo, "avatar": avatar}) 
        save_state()

        return RedirectResponse("/")
    return HTMLResponse("Échec de l'authentification Steam.", status_code=401)

@app.post("/logout", response_class=HTMLResponse)
async def logout(request: Request):
    state.update({"steam_id": None, "pseudo": None, "avatar": None})
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)
    return templates.TemplateResponse(request=request, name="index.html", context={
        "steam_id": None, "pseudo": None, "avatar": None
    })

@app.get("/inventory", response_class=HTMLResponse)
async def get_inventory(request: Request, force_refresh: bool = False, db: Session = Depends(get_db)):
    if not state["steam_id"]:
        return HTMLResponse("<p>Veuillez vous connecter.</p>")
    items = await fetch_inventory(state["steam_id"], db, force_refresh=force_refresh) 
    return templates.TemplateResponse(request=request, name="cards.html", context={"items": items, "force_refresh": force_refresh})

@app.post("/update_price")
async def update_price(
    asset_id: str = Form(...), 
    price: float = Form(...), 
    name: Optional[str] = Form(None),
    batches: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    skin = db.query(database.Skin).filter(database.Skin.asset_id == asset_id).first()
    if skin:
        skin.purchase_price = price 
        if batches is not None:
            skin.batches = batches 
    else:
        db.add(database.Skin(steam_id=state["steam_id"], asset_id=asset_id, name=name, purchase_price=price, batches=batches))
    db.commit()
    return {"status": "success"}

@app.get("/api/csfloat_price")
async def get_csfloat_price(market_hash_name: str, float_value: Optional[str] = None, force_refresh: bool = False, db: Session = Depends(get_db)):
    try:
        target_float = float(float_value) if float_value and float_value != "N/A" else None
    except ValueError:
        target_float = None

    endpoint = f"csfloat_{market_hash_name}_{round(target_float, 3)}" if target_float is not None else f"csfloat_{market_hash_name}"
    
    now = datetime.datetime.utcnow()
    cache = db.query(database.APICache).filter(database.APICache.endpoint == endpoint).first()

    listings = []
    if not force_refresh and cache and (now - cache.last_called).total_seconds() < 900 and cache.response_data: 
        listings = json.loads(cache.response_data) 
    else:
        api_key = os.getenv("CSFLOAT_API_KEY")
        url = f"https://csfloat.com/api/v1/listings?market_hash_name={urllib.parse.quote(market_hash_name)}&limit=50&type=buy_now"
        if target_float is not None:
            url += f"&min_float={max(0.0, target_float - 0.05):.4f}&max_float={min(1.0, target_float + 0.05):.4f}"

        headers = {"User-Agent": "Mozilla/5.0"}
        if api_key: headers["Authorization"] = api_key
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    listings = data if isinstance(data, list) else data.get("data", [])
                    
                    cache_data = json.dumps(listings)
                    if cache:
                        cache.last_called, cache.response_data = now, cache_data 
                    else:
                        db.add(database.APICache(endpoint=endpoint, last_called=now, response_data=cache_data))
                    db.commit()
        except Exception as e:
            print(f"Erreur API CSFloat : {e}")

    if not listings:
        return {"error": "Aucune donnée de marché disponible"}

    USD_TO_EUR = await get_live_exchange_rate(db)
    is_stattrak_target = "StatTrak" in market_hash_name
    is_souvenir_target = "Souvenir" in market_hash_name
    is_star_target = "★" in market_hash_name
    
    valid_listings = []
    for item in listings:
        if 'price' not in item or 'item' not in item: 
            continue
            
        item_info = item['item']
        listing_name = item_info.get('market_hash_name', "")
        
        st_val = item_info.get('stattrak')
        if ((st_val is not None and st_val != -1) or "StatTrak" in listing_name) != is_stattrak_target: continue
        if (item_info.get('is_souvenir', False) or "Souvenir" in listing_name) != is_souvenir_target: continue
        if ("★" in listing_name) != is_star_target: continue
        
        valid_listings.append({
            "price_eur": (item['price'] / 100.0) * USD_TO_EUR,
            "float_value": item_info.get('float_value')
        })

    if not valid_listings:
        return {"error": "Aucun prix correspondant à cette catégorie exacte"}

    if target_float is None:
        return {"average": sum(x['price_eur'] for x in valid_listings) / len(valid_listings), "low_precision": True, "count": len(valid_listings), "margin": None}

    for margin in (0.01, 0.02, 0.03, 0.04, 0.05):
        range_prices = [x['price_eur'] for x in valid_listings if x['float_value'] is not None and abs(x['float_value'] - target_float) <= margin]
        if range_prices:
            return {"average": sum(range_prices) / len(range_prices), "low_precision": margin > 0.02, "count": len(range_prices), "margin": margin}

    prices_with_float = [x['price_eur'] for x in valid_listings if x['float_value'] is not None]
    if prices_with_float:
        return {"average": sum(prices_with_float) / len(prices_with_float), "low_precision": True, "count": len(prices_with_float), "margin": "max (0.05)"}

    return {"error": "Aucun prix correspondant avec float"}
