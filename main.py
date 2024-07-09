from typing import List, Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException
import time
from fastapi import FastAPI, Query, HTTPException
import logging

app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def search_napista(driver: webdriver.Chrome, car_model: str, car_marca: str,
                   transmissao: Optional[str] = None, preco_a_partir: Optional[str] = None,
                   preco_ate: Optional[str] = None, km: Optional[str] = None) -> List[dict]:
    max_retries = 5
    attempt = 0

    while attempt < max_retries:
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

            car_names = []
            car_prices = []

            while True:
                try:
                    results_napista = driver.find_elements(By.XPATH, '//div[contains(@class, "iRYCmh")]')

                    if results_napista:
                        for napista_result in results_napista:
                            try:
                                napista_car_name = napista_result.find_element(By.XPATH,
                                                                               './/h2[contains(@class, " hXsWso")]').text
                                napista_car_price = napista_result.find_element(By.XPATH,
                                                                                './/div[contains(@class, " klMQDM")]').text

                                car_names.append(napista_car_name)
                                car_prices.append(napista_car_price)

                            except StaleElementReferenceException:
                                logger.error("Encountered StaleElementReferenceException. Retrying...")
                                break

                            except Exception as e:
                                logger.error(f"Error processing napista result: {e}")

                        return [{"name": name, "price": price} for name, price in zip(car_names, car_prices)]

                    else:
                        logger.info("No results found. Retrying...")
                        time.sleep(2)

                except StaleElementReferenceException:
                    logger.error("Encountered StaleElementReferenceException outside. Retrying...")
                    time.sleep(2)

                except Exception as e:
                    logger.error(f"Error in search_napista: {e}")
                    time.sleep(2)

        except NoSuchElementException as e:
            logger.error(f"Element not found: {e}")
        except Exception as e:
            logger.error(f"Error in search_napista attempt {attempt}: {e}")

        attempt += 1
        logger.info(f"Retrying... Attempt {attempt}/{max_retries}")
        time.sleep(5)  # Wait before retrying

    return []

@app.get("/data")
async def get_data(car_marca: str = Query(..., description="Marca do carro"),
                   car_model: str = Query(..., description="Modelo do carro"),
                   transmissao: Optional[str] = Query(None, description="Tipo de transmissão"),
                   preco_a_partir: Optional[str] = Query(None, description="Preço a partir de"),
                   preco_ate: Optional[str] = Query(None, description="Preço até"),
                   km: Optional[str] = Query(None, description="Limite de quilometragem")):
    try:
        chrome_options = webdriver.ChromeOptions()
        #chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        while True:
            driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)

            napista_results = search_napista(driver, car_model, car_marca, transmissao, preco_a_partir, preco_ate, km)

            driver.quit()

            if napista_results:
                return {
                    "napista_results": napista_results
                }
            else:
                logger.info("Retrying data retrieval as napista results are not present.")
                time.sleep(5)

    except Exception as e:
        logger.error(f"Error in get_data: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
