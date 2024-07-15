from typing import Optional, List, Dict
from fastapi import FastAPI, Query, HTTPException, Body
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
import time
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
import concurrent.futures

app = FastAPI()

class HrefList(BaseModel):
    hrefs: List[str]
    name_value: str
    phone_value: Optional[str]
    email_value: Optional[str]
    message_value: str

def create_driver() -> webdriver.Chrome:
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument('window-size=1920x1080')
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--disable-logging")
    service = ChromeService(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

def split_list(lst, n):
    return [lst[i:i + n] for i in range(0, len(lst), n)]

def search_hrefs(car_model: str = Query(..., description="Modelo do carro"),
                 car_marca: str = Query(..., description="Marca do carro"),
                 transmissao: Optional[str] = Query(None, description="Tipo de transmissão"),
                 preco_a_partir: Optional[str] = Query(None, description="Preço a partir de"),
                 preco_ate: Optional[str] = Query(None, description="Preço até"),
                 km: Optional[str] = Query(None, description="Quilometragem máxima")) -> List[str]:
    driver = create_driver()
    hrefs = []

    try:
        url_parts = [car_marca, car_model]

        if transmissao:
            url_parts.append(transmissao)
        if preco_a_partir:
            url_parts.append(preco_a_partir)
        if preco_ate:
            url_parts.append(preco_ate)
        if km:
            url_parts.append(km)

        url = 'https://napista.com.br/busca/' + '-'.join(url_parts)
        driver.get(url)
        time.sleep(3)

        page_count = 1
        total_hrefs = 0

        try:
            select_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, 'select'))
            )
            if not select_element.is_displayed():
                driver.execute_script("arguments[0].style.display = 'block';", select_element)
            select = Select(select_element)
            select.select_by_visible_text('Sem limite')
        except TimeoutException:
            print("Dropdown para limite de distância não encontrado ou não clicável.")

        time.sleep(2)

        while True:
            links_elements = driver.find_elements(By.XPATH,
                                                  './/a[starts-with(@href, "/anuncios/") and not(contains(@href, "lead/simular"))]')
            current_hrefs = [link.get_attribute("href") for link in links_elements]
            hrefs.extend(current_hrefs)
            total_hrefs += len(current_hrefs)
            print(f"Página {page_count} - Total de hrefs encontrados: {len(current_hrefs)}")

            try:
                next_button = driver.find_element(By.XPATH,
                                                  '//button[contains(@class, "sc-7b897988-0") and contains(., "Próxima")]')
                if next_button.is_enabled():
                    driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                    driver.execute_script("arguments[0].click();", next_button)
                    time.sleep(1)
                    page_count += 1
                else:
                    break
            except NoSuchElementException:
                break

        print(f"Total de páginas: {page_count}")
        print(f"Total de hrefs encontrados: {total_hrefs}")

        if not hrefs:
            print("Nenhum resultado encontrado.")

    except Exception as e:
        print(f"Erro ao realizar a busca: {str(e)}")
        raise

    finally:
        driver.quit()

    return hrefs

def capture_car_info(driver: webdriver.Chrome, href: str, name_value: str, phone_value: Optional[str], email_value: Optional[str], message_value: str) -> dict:
    try:
        driver.get(href)

        car_info = {"href": href}

        def get_element_text(xpath: str, timeout=3) -> str:
            try:
                element = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.XPATH, xpath))
                )
                return element.text.strip()
            except TimeoutException:
                return ""

        car_info["name"] = get_element_text('/html/body/div[1]/div/div[2]/div/div[2]/div[1]/div/div[2]/h1')
        car_info["price"] = get_element_text('/html/body/div[1]/div/div[2]/div/div[2]/div[2]/div/div[1]/div/div[1]/div/div')
        car_info["localidade"] = get_element_text('/html/body/div[1]/div/div[2]/div/div[2]/div[1]/div/div[2]/div/div[2]')
        car_info["km"] = get_element_text('//li[div[div[text()="Quilometragem"]]]/div[@variant="subheading" and @color="text-primary"]')
        car_info["cambio"] = get_element_text('//li[div[div[text()="Câmbio"]]]/div[@variant="subheading" and @color="text-primary"]')
        car_info["ano"] = get_element_text('//li[div[div[text()="Ano"]]]/div[@variant="subheading" and @color="text-primary"]')
        car_info["loja"] = get_element_text('//h3[@class="sc-b35e10ef-0 jplEHn"]')

        driver.get(f"{href}/lead/contato")

        if "/lead/contato" in driver.current_url:
            try:
                nao_sou_eu_element = WebDriverWait(driver, 2).until(
                    EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div/div[2]/div/div[2]/div/div/div/form/div/div[1]/div/div[2]/a/div'))
                )
                if nao_sou_eu_element.is_displayed():
                    nao_sou_eu_element.click()
            except TimeoutException:
                pass

            if name_value:
                name_input = WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.NAME, 'client.name')))
                name_input.clear()
                name_input.send_keys(name_value)

            if phone_value:
                phone_input = WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.NAME, 'client.phone')))
                phone_input.clear()
                phone_input.send_keys(phone_value)

            if email_value:
                email_input = WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.NAME, 'client.email')))
                email_input.clear()
                email_input.send_keys(email_value)

            if message_value:
                message_input = WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.NAME, 'messageToSeller')))
                message_input.clear()
                message_input.send_keys(message_value)

            try:
                cookie_banner = driver.find_element(By.ID, 'onetrust-close-btn-container')
                if cookie_banner.is_displayed():
                    cookie_banner.click()
                    time.sleep(1)
            except NoSuchElementException:
                pass

            try:
                submit_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, '/html/body/div[1]/div/div[2]/div/div[2]/div/div/div/form/div/div[4]/button'))
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
                time.sleep(0.5)
                submit_button.click()
                time.sleep(1)
                car_info['status_message'] = "Mensagem enviada com sucesso"
            except (TimeoutException, ElementClickInterceptedException):
                car_info['status_message'] = "Falha ao enviar mensagem"
        else:
            car_info['status_message'] = "Página de contato não encontrada"

        return car_info

    except Exception as e:
        print(f"Erro ao capturar informações do carro: {str(e)}")
        return {}

def process_car_links(hrefs: List[str], name_value: str, phone_value: Optional[str], email_value: Optional[str], message_value: str) -> List[dict]:
    car_details_list = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(capture_car_info, create_driver(), href, name_value, phone_value, email_value, message_value)
            for href in hrefs
        ]
        for future in concurrent.futures.as_completed(futures):
            car_details_list.append(future.result())

    return car_details_list

@app.get("/search_hrefs")
async def search_and_process(car_model: str = Query(..., description="Modelo do carro"),
                             car_marca: str = Query(..., description="Marca do carro"),
                             transmissao: Optional[str] = Query(None, description="Tipo de transmissão"),
                             preco_a_partir: Optional[str] = Query(None, description="Preço a partir de"),
                             preco_ate: Optional[str] = Query(None, description="Preço até"),
                             km: Optional[str] = Query(None, description="Quilometragem máxima")) -> List[List[str]]:
    try:
        hrefs = search_hrefs(car_model, car_marca, transmissao, preco_a_partir, preco_ate, km)
        if not hrefs:
            raise HTTPException(status_code=404, detail="No car listings found")

        # Dividir a lista de URLs em sublistas de blocos de 10
        href_blocks = split_list(hrefs, 10)
        return href_blocks

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.post("/capture_car_data")
async def capture_car_data(data: HrefList) -> List[Dict]:
    try:
        car_details_list = process_car_links(data.hrefs, data.name_value, data.phone_value, data.email_value, data.message_value)
        return car_details_list

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
