from typing import List, Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from fastapi import FastAPI, Query, HTTPException
import time

app = FastAPI()

def search_napista(driver: webdriver.Chrome, car_model: str, car_marca: str,
                   transmissao: Optional[str] = None, preco_a_partir: Optional[str] = None,
                   preco_ate: Optional[str] = None, km: Optional[str] = None,
                   name_value: Optional[str] = None, phone_value: Optional[str] = None,
                   email_value: Optional[str] = None, message_value: Optional[str] = None) -> List[dict]:
    max_retries = 5
    attempt = 0
    page_number = 1
    cars_info = []

    while attempt < max_retries:
        try:
            while True:
                url_parts = [car_marca, car_model]

                if transmissao:
                    url_parts.append(transmissao)
                if preco_a_partir:
                    url_parts.append(preco_a_partir)
                if preco_ate:
                    url_parts.append(preco_ate)
                if km:
                    url_parts.append(km)

                url = f'https://napista.com.br/busca/' + '-'.join(url_parts) + f'?page={page_number}'
                driver.get(url)
                time.sleep(1.5)  # Reduzido de 3 para 1.5

                # Certifique-se de que o elemento select está visível e interaja com ele
                try:
                    select_element = WebDriverWait(driver, 5).until(  # Reduzido de 10 para 5
                        EC.presence_of_element_located((By.TAG_NAME, 'select'))
                    )

                    # Verifique se o elemento está visível
                    if select_element.is_displayed():
                        select = Select(select_element)
                        select.select_by_visible_text('Sem limite')
                    else:
                        driver.execute_script("arguments[0].style.display = 'block';", select_element)
                        select = Select(select_element)
                        select.select_by_visible_text('Sem limite')

                except TimeoutException:
                    pass

                time.sleep(5)  # Reduzido de 3 para 1.5

                # Captura todos os links dos carros
                links_elements = WebDriverWait(driver, 3).until(  # Reduzido de 5 para 3
                    EC.presence_of_all_elements_located((By.XPATH, './/a[starts-with(@href, "/anuncios/") and not(contains(@href, "lead/simular"))]'))
                )
                time.sleep(3)
                hrefs = [link.get_attribute("href") for link in links_elements]
                print(f"Total de hrefs encontrados na página {page_number}: {len(hrefs)}")

                # Itera sobre os links para coletar informações de cada carro
                for href in hrefs:
                    try:
                        driver.get(href)
                        time.sleep(1)  # Reduzido de 2 para 1

                        car_name = WebDriverWait(driver, 1).until(  # Reduzido de 1 para 0.5
                            EC.presence_of_element_located(
                                (By.XPATH, '/html/body/div[1]/div/div[2]/div/div[2]/div[1]/div/div[2]/h1'))
                        ).text

                        car_price = WebDriverWait(driver, 1).until(
                            EC.presence_of_element_located((By.XPATH,
                                                            '/html/body/div[1]/div/div[2]/div/div[2]/div[2]/div/div[1]/div/div[1]/div[1]/div'))
                        ).text

                        car_localidade = WebDriverWait(driver, 1).until(
                            EC.presence_of_element_located((By.XPATH,
                                                            '/html/body/div[1]/div/div[2]/div/div[2]/div[1]/div/div[2]/div/div[2]'))
                        ).text

                        car_km = WebDriverWait(driver, 1).until(
                            EC.presence_of_element_located((By.XPATH,
                                                            '//li[div[div[text()="Quilometragem"]]]/div[@variant="subheading" and @color="text-primary"]'))
                        ).text

                        car_cambio = WebDriverWait(driver, 1).until(
                            EC.presence_of_element_located((By.XPATH,
                                                            '//li[div[div[text()="Câmbio"]]]/div[@variant="subheading" and @color="text-primary"]'))
                        ).text

                        car_ano = WebDriverWait(driver, 1).until(
                            EC.presence_of_element_located((By.XPATH,
                                                            '//li[div[div[text()="Ano"]]]/div[@variant="subheading" and @color="text-primary"]'))
                        ).text

                        car_loja = WebDriverWait(driver, 1).until(
                            EC.presence_of_element_located((By.XPATH,
                                                            '/html/body/div[1]/div/div[2]/div/div[2]/div[1]/div/div[11]/div[1]/h3'))
                        ).text

                        car_info = {"name": car_name, "price": car_price, "localidade": car_localidade, "link": href, "km": car_km, "cambio": car_cambio, "ano": car_ano, "loja": car_loja}

                        lead_contact_link = WebDriverWait(driver, 0.5).until(  # Reduzido de 1 para 0.5
                            EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div/div[2]/div/div[2]/div[2]/div/div[1]/a[2]'))
                        )
                        lead_contact_link.click()
                        time.sleep(0.5)  # Reduzido de 1 para 0.5

                        if "/lead/contato" in driver.current_url:

                            try:
                                # Verifique se o elemento "Não sou eu" está presente e visível
                                """try:
                                    nao_sou_eu_element = WebDriverWait(driver, 2.5).until(  # Reduzido de 5 para 2.5
                                        EC.presence_of_element_located((By.XPATH,
                                                                        '/html/body/div[1]/div/div[2]/div/div[2]/div/div/div/form/div/div[1]/div/div[2]/a/div'))
                                    )
                                    if nao_sou_eu_element.is_displayed():
                                        nao_sou_eu_element.click()
                                        print("Clicked on 'Não sou eu' link")
                                        time.sleep(1)  # Reduzido de 2 para 1
                                except TimeoutException:
                                    print("Elemento 'Não sou eu' não encontrado, preenchendo o formulário diretamente")

                                # Inserir valores nos campos de input
                                if name_value:
                                    driver.find_element(By.NAME, 'client.name').send_keys(name_value)
                                if phone_value:
                                    driver.find_element(By.NAME, 'client.phone').send_keys(phone_value)
                                if email_value:
                                    driver.find_element(By.NAME, 'client.email').send_keys(email_value)
                                if message_value:
                                    driver.find_element(By.NAME, 'messageToSeller').send_keys(message_value)

                                # Esperar um momento para que os valores sejam refletidos na interface
                                time.sleep(0.5)  # Reduzido de 1 para 0.5

                                # Obter os valores dos campos de input e imprimir
                                if name_value:
                                    name_value = driver.find_element(By.NAME, 'client.name').get_attribute("value")
                                    print(f'Client Name: {name_value}')
                                if phone_value:
                                    phone_value = driver.find_element(By.NAME, 'client.phone').get_attribute("value")
                                    print(f'Client Phone: {phone_value}')
                                if email_value:
                                    email_value = driver.find_element(By.NAME, 'client.email').get_attribute("value")
                                    print(f'Client Email: {email_value}')
                                if message_value:
                                    message_value = driver.find_element(By.NAME, 'messageToSeller').get_attribute("value")
                                    print(f'Message to Seller: {message_value}')"""

                                # Role para o botão de envio
                                submit_button = WebDriverWait(driver, 2.5).until(  # Reduzido de 5 para 2.5
                                    EC.element_to_be_clickable((By.XPATH,
                                                                '/html/body/div[1]/div/div[2]/div/div[2]/div/div/div/form/div/div[4]/button'))
                                )

                                # Usando JavaScript para clicar no botão
                                driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
                                driver.execute_script("arguments[0].click();", submit_button)

                                # Adicione a mensagem enviada ao dicionário do carro
                                car_info['status_message'] = "Mensagem enviada com sucesso"

                            except TimeoutException:
                                print("TimeoutException: Could not find submit button or inputs")
                            except Exception as e:
                                print(f"Exception: {e}")

                        cars_info.append(car_info)

                    except NoSuchElementException:
                        pass
                    except TimeoutException:
                        pass
                    except Exception:
                        pass

                if len(hrefs) < 48:
                    break  # Sai do loop se houver menos de 48 carros na página atual

                page_number += 1  # Incrementa o número da página para o próximo loop

            return cars_info

        except Exception:
            pass

        attempt += 1
        time.sleep(2.5)  # Reduzido de 5 para 2.5

    return []

@app.get("/data")
async def get_data(car_marca: str = Query(..., description="Marca do carro"),
                   car_model: str = Query(..., description="Modelo do carro"),
                   transmissao: Optional[str] = Query(None, description="Tipo de transmissão"),
                   preco_a_partir: Optional[str] = Query(None, description="Preço a partir de"),
                   preco_ate: Optional[str] = Query(None, description="Preço até"),
                   km: Optional[str] = Query(None, description="Limite de quilometragem"),
                   name_value: Optional[str] = Query(None, description="Client Name"),
                   phone_value: Optional[str] = Query(None, description="Client Phone"),
                   email_value: Optional[str] = Query(None, description="Client Email"),
                   message_value: Optional[str] = Query(None, description="Message to Seller")):
    try:
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--disable-logging")

        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)

        napista_results = search_napista(driver, car_model, car_marca, transmissao, preco_a_partir, preco_ate, km,
                                         name_value, phone_value, email_value, message_value)

        if napista_results:
            return {
                "napista_results": napista_results
            }
        else:
            time.sleep(2.5)  # Reduzido de 5 para 2.5

    except Exception:
        raise HTTPException(status_code=500, detail="Internal Server Error")

    finally:
        if driver:
            driver.quit()
