import datetime
import json
import httpx
import os
import urllib.parse
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

load_dotenv()

import database

database.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Paffloat")
templates = Jinja2Templates(directory="templates")

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

SESSION_FILE = "session.json"

def load_state():
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

@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, steam_id: str = Form(...)):
    pseudo, avatar = await get_steam_profile(steam_id)
    state["steam_id"] = steam_id
    state["pseudo"] = pseudo
    state["avatar"] = avatar

    save_state()
    
    return templates.TemplateResponse(request=request, name="inventory_section.html", context={"steam_id": steam_id, "pseudo": pseudo, "avatar": avatar})

@app.post("/logout", response_class=HTMLResponse)
async def logout(request: Request):
    state["steam_id"] = None
    state["pseudo"] = None
    state["avatar"] = None
    
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)

    return templates.TemplateResponse(request=request, name="index.html", context={"steam_id": None, "pseudo": None, "avatar": None})

def get_float_category(float_value):
    if float_value is None: return "N/A"
    if float_value < 0.07: return "FN"
    if float_value < 0.15: return "MW"
    if float_value < 0.38: return "FT"
    if float_value < 0.45: return "WW"
    return "BS"

async def get_steam_profile(steam_id: str):
    url = f"https://steamcommunity.com/profiles/{steam_id}/?xml=1"
    pseudo = steam_id
    avatar = "https://avatars.steamstatic.com/fef49e7fa7e1997310d705b2a6158ff8dc1cdfeb_full.jpg" # Image par défaut
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=5.0)
            if response.status_code == 200:
                text = response.text

                p_start = text.find("<steamID><![CDATA[")
                if p_start != -1:
                    p_start += len("<steamID><![CDATA[")
                    p_end = text.find("]]></steamID>", p_start)
                    if p_end != -1:
                        pseudo = text[p_start:p_end]

                a_start = text.find("<avatarFull><![CDATA[")
                if a_start != -1:
                    a_start += len("<avatarFull><![CDATA[")
                    a_end = text.find("]]></avatarFull>", a_start)
                    if a_end != -1:
                        avatar = text[a_start:a_end]
    except Exception as e:
        print(f"Erreur lors de la récupération du profil Steam: {e}")
    
    return pseudo, avatar

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={"steam_id": state["steam_id"], "pseudo": state["pseudo"], "avatar": state.get("avatar")})

def get_item_type(tags):
    for tag in tags:
        cat = tag.get("category")
        int_name = tag.get("internal_name")
        
        if cat == "Weapon" or int_name == "CSGO_Type_Knife": return "armes"
        if int_name == "CSGO_Type_Hands": return "gants"
        if int_name == "Type_CustomPlayer": return "agents"
        if int_name == "CSGO_Type_WeaponCase": return "caisses"
        if int_name == "CSGO_Tool_Sticker": return "stickers"
        if int_name == "CSGO_Tool_Keychain": return "porte-cles"
        if int_name == "CSGO_Tool_Patch": return "ecussons"
        if int_name == "CSGO_Type_Collectible": return "pins"
        if int_name == "CSGO_Type_MusicKit": return "kits_musique"
    return "autre"
    
async def fetch_inventory(steam_id: str, db: Session):
    endpoint = f"steam_inv_{steam_id}"
    cache = db.query(database.APICache).filter(database.APICache.endpoint == endpoint).first()
    now = datetime.datetime.utcnow()

    if cache and (now - cache.last_called).total_seconds() < 10:
        if cache.response_data:
            items = json.loads(cache.response_data)

            saved_skins = db.query(database.Skin).filter(database.Skin.steam_id == steam_id).all()
            db_skins_map = {s.asset_id: s for s in saved_skins}
            
            for item in items:
                if item["asset_id"] in db_skins_map:
                    item["purchase_price"] = db_skins_map[item["asset_id"]].purchase_price
            
            return items

    url = f"https://steamcommunity.com/inventory/{steam_id}/730/2?l=fenglish&count=50"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code == 403:
                print(f"Inventaire privé ou accès refusé pour {steam_id}")
                return []
            
            response.raise_for_status()
            data = response.json()
            
            items = []
            if "descriptions" in data and "assets" in data:
                saved_skins = db.query(database.Skin).filter(database.Skin.steam_id == steam_id).all()
                db_skins_map = {s.asset_id: s for s in saved_skins}
                desc_map = {f"{d['classid']}_{d['instanceid']}": d for d in data["descriptions"]}

                asset_props_map = {}
                if "asset_properties" in data:
                    for prop_group in data["asset_properties"]:
                        asset_id = str(prop_group.get("assetid"))
                        props = prop_group.get("asset_properties", [])
                        
                        float_val = None
                        seed_val = None

                        for p in props:
                            if p.get("propertyid") == 1:
                                seed_val = p.get("int_value")
                            elif p.get("propertyid") == 2:
                                float_val = float(p.get("float_value"))
                        
                        asset_props_map[asset_id] = {
                            "float": float_val,
                            "seed": seed_val
                        }

                stackables_map = {}

                for asset in data["assets"]:
                    desc_key = f"{asset['classid']}_{asset['instanceid']}"
                    desc = desc_map.get(desc_key, {})
                    
                    if desc.get("marketable") != 1:
                        continue
                        
                    asset_id = str(asset["assetid"])
                    raw_name = desc.get("name", "Objet inconnu")
                    clean_name = raw_name.split(" (")[0]

                    item_type = get_item_type(desc.get("tags", []))

                    rarity_color = "2c2c2c"
                    for tag in desc.get("tags", []):
                        if tag.get("category") == "Rarity" and "color" in tag:
                            rarity_color = tag["color"]
                            break

                    stackable_types = [
                        "CSGO_Type_WeaponCase",
                        "CSGO_Tool_Sticker",
                        "CSGO_Tool_Keychain",
                        "CSGO_Tool_Patch",
                        "CSGO_Type_Collectible"
                    ]
                    is_stackable = any(tag.get("internal_name") in stackable_types for tag in desc.get("tags", []))

                    if is_stackable:
                        if clean_name in stackables_map:
                            stackables_map[clean_name]["count"] += 1
                            
                            if stackables_map[clean_name]["purchase_price"] == 0.00 and asset_id in db_skins_map:
                                old_price = db_skins_map[asset_id].purchase_price
                                old_batches = getattr(db_skins_map[asset_id], "batches", None)
                                stackables_map[clean_name]["purchase_price"] = old_price
                                stackables_map[clean_name]["batches"] = old_batches
                                
                                if clean_name not in db_skins_map:
                                    new_skin = database.Skin(steam_id=steam_id, asset_id=clean_name, name=clean_name, purchase_price=old_price, batches=old_batches)
                                    db.add(new_skin)
                                    db_skins_map[clean_name] = new_skin
                        else:
                            price = 0.00
                            batches_str = None
                            if clean_name in db_skins_map:
                                price = db_skins_map[clean_name].purchase_price
                                batches_str = getattr(db_skins_map[clean_name], "batches", None)
                            elif asset_id in db_skins_map:
                                price = db_skins_map[asset_id].purchase_price
                                batches_str = getattr(db_skins_map[asset_id], "batches", None)
                                
                                if clean_name not in db_skins_map:
                                    new_skin = database.Skin(steam_id=steam_id, asset_id=clean_name, name=clean_name, purchase_price=price, batches=batches_str)
                                    db.add(new_skin)
                                    db_skins_map[clean_name] = new_skin

                            stackables_map[clean_name] = {
                                "asset_id": clean_name,
                                "name": clean_name,
                                "image_url": f"https://community.cloudflare.steamstatic.com/economy/image/{desc.get('icon_url')}",
                                "is_stackable": True, 
                                "count": 1,
                                "purchase_price": price,
                                "batches": batches_str,
                                "rarity_color": rarity_color,
                                "item_type": item_type 
                            }
                    else:
                        item = {
                            "asset_id": asset_id,
                            "name": clean_name,
                            "market_hash_name": desc.get("market_hash_name", raw_name),
                            "image_url": f"https://community.cloudflare.steamstatic.com/economy/image/{desc.get('icon_url')}",
                            "float_value": "N/A",
                            "float_category": "N/A",
                            "seed": "N/A",
                            "purchase_price": db_skins_map[asset_id].purchase_price if asset_id in db_skins_map else 0.00,
                            "is_stackable": False,
                            "rarity_color": rarity_color,
                            "item_type": item_type
                        }
   
                        db_skin = db_skins_map.get(asset_id)
                        
                        if db_skin and db_skin.float_value is not None:
                            item["float_value"] = db_skin.float_value
                            item["float_category"] = db_skin.float_category or get_float_category(db_skin.float_value)
                            item["seed"] = db_skin.seed if db_skin.seed is not None else "N/A"
                        else:
                            if asset_id in asset_props_map:
                                f_val = asset_props_map[asset_id]["float"]
                                s_val = asset_props_map[asset_id]["seed"]
                                
                                if f_val is not None:
                                    item["float_value"] = f_val
                                    item["float_category"] = get_float_category(f_val)
                                    item["seed"] = s_val if s_val is not None else "N/A"

                                    if not db_skin:
                                        new_skin = database.Skin(
                                            steam_id=steam_id,
                                            asset_id=asset_id,
                                            name=clean_name,
                                            float_value=f_val,
                                            float_category=get_float_category(f_val),
                                            seed=s_val,
                                            purchase_price=0.0
                                        )
                                        db.add(new_skin)
                                    else:
                                        db_skin.float_value = f_val
                                        db_skin.float_category = get_float_category(f_val)
                                        db_skin.seed = s_val
                                        
                        items.append(item)

                items.extend(stackables_map.values())

            cache_data = json.dumps(items)
            if cache:
                cache.last_called = now
                cache.response_data = cache_data
            else:
                new_cache = database.APICache(endpoint=endpoint, last_called=now, response_data=cache_data)
                db.add(new_cache)
            db.commit()
            return items
            
    except Exception as e:
        print(f"Erreur API Steam: {e}")
        if cache and cache.response_data:
            return json.loads(cache.response_data)
        return []

@app.get("/inventory", response_class=HTMLResponse)
async def get_inventory(request: Request, db: Session = Depends(get_db)):
    if not state["steam_id"]:
        return "<p>Veuillez vous connecter.</p>"
        
    items = await fetch_inventory(state["steam_id"], db)
    return templates.TemplateResponse(request=request, name="cards.html", context={"items": items})

@app.get("/api/csfloat_price")
async def get_csfloat_price(market_hash_name: str, float_value: str = None, db: Session = Depends(get_db)):
    """Récupère le prix moyen sur CSFloat en filtrant par type (StatTrak, Souvenir, ★, Normal)."""
    endpoint = f"csfloat_{market_hash_name}"
    cache = db.query(database.APICache).filter(database.APICache.endpoint == endpoint).first()
    now = datetime.datetime.utcnow()

    is_stattrak_target = "StatTrak" in market_hash_name
    is_souvenir_target = "Souvenir" in market_hash_name
    is_star_target = "★" in market_hash_name
    
    listings = []

    if cache and (now - cache.last_called).total_seconds() < 900:
        if cache.response_data:
            listings = json.loads(cache.response_data)
    else:
        api_key = os.getenv("CSFLOAT_API_KEY")
        url = f"https://csfloat.com/api/v1/listings?market_hash_name={urllib.parse.quote(market_hash_name)}&limit=50&type=buy_now"
        headers = {"User-Agent": "Mozilla/5.0", "Authorization": api_key}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=10.0)
                if response.status_code == 200:
                    listings = response.json().get("data", [])
                    # Mise à jour du cache
                    cache_data = json.dumps(listings)
                    if cache:
                        cache.last_called = now
                        cache.response_data = cache_data
                    else:
                        db.add(database.APICache(endpoint=endpoint, last_called=now, response_data=cache_data))
                    db.commit()
        except Exception:
            listings = []

    if not listings:
        return {"error": "Aucune donnée"}

    USD_TO_EUR = await get_live_exchange_rate(db)
    try:
        target_float = float(float_value) if float_value and float_value != "N/A" else None
    except ValueError:
        target_float = None

    all_prices = []
    range_prices = []

    for item in listings:
        if 'price' not in item or 'item' not in item:
            continue
            
        item_info = item.get('item', {})
        listing_name = item_info.get('market_hash_name', "")
        st_val = item_info.get('stattrak')
        is_st_listing = (st_val is not None and st_val != -1) or "StatTrak" in listing_name
        is_souv_listing = item_info.get('is_souvenir', False) or "Souvenir" in listing_name
        is_star_listing = "★" in listing_name

        if (is_st_listing != is_stattrak_target or 
            is_souv_listing != is_souvenir_target or 
            is_star_listing != is_star_target):
            continue
        
        price_eur = (item['price'] / 100.0) * USD_TO_EUR
        all_prices.append(price_eur)

        item_f = item_info.get('float_value')
        if target_float is not None and item_f is not None:
            if abs(item_f - target_float) <= 0.02:
                range_prices.append(price_eur)

    if target_float is not None and range_prices:
        avg = sum(range_prices) / len(range_prices)
        return {"average": avg, "low_precision": False, "count": len(range_prices)}
    elif all_prices:
        avg = sum(all_prices) / len(all_prices)
        return {"average": avg, "low_precision": True, "count": len(all_prices)}
    
    return {"error": "Aucun prix correspondant"}
    
@app.post("/update_price")
async def update_price(
    asset_id: str = Form(...), 
    price: float = Form(...), 
    name: str = Form(None),
    batches: str = Form(None),
    db: Session = Depends(get_db)
):
    skin = db.query(database.Skin).filter(database.Skin.asset_id == asset_id).first()
    
    if skin:
        skin.purchase_price = price
        if batches is not None:
            skin.batches = batches
    else:
        new_skin = database.Skin(
            steam_id=state["steam_id"],
            asset_id=asset_id,
            name=name,
            purchase_price=price,
            batches=batches
        )
        db.add(new_skin)
    
    db.commit()
    return {"status": "success"}

async def get_live_exchange_rate(db: Session):
    endpoint = "currency_usd_eur"
    cache = db.query(database.APICache).filter(database.APICache.endpoint == endpoint).first()
    now = datetime.datetime.utcnow()

    if cache and (now - cache.last_called).total_seconds() < 43200:
        return float(cache.response_data)

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.frankfurter.dev/v1/latest?base=USD&symbols=EUR", 
                headers=headers, 
                timeout=5.0
            )
            
            if response.status_code == 200:
                rate = response.json()["rates"]["EUR"]

                if cache:
                    cache.last_called = now
                    cache.response_data = str(rate)
                else:
                    new_cache = database.APICache(endpoint=endpoint, last_called=now, response_data=str(rate))
                    db.add(new_cache)
                db.commit()
                return rate
            else:
                print(f"--- ERREUR HTTP API CHANGE ---")
                print(f"Code : {response.status_code}")
                print(f"Détail : {response.text}")
                
    except Exception as e:
        print(f"--- ERREUR API TAUX DE CHANGE ---")
        print(f"Type d'erreur : {type(e).__name__}")
        print(f"Message : {e}")
        print(f"----------------------------------")

    if cache:
        return float(cache.response_data)

    return 0.87
