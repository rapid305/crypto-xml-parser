import os
import httpx
import xml.etree.ElementTree as ET
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

CARDS = ("CARDRUB" , "TCSBRUB" , "SBERRUB", "SBPRUB")


class ParseService:
    def __init__(self):
        self.parse_url = os.getenv('PARSE_URL')
        self.timeout = 15
        # # Заголовки для имитации браузера
        # self.headers = {
        #     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        #     "Accept": "application/xml, text/xml, */*",
        #     "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        # }

        if not self.parse_url:
            logger.warning("PARSE_URL is not set!")

    async def get_request(self) -> str:
        """Makes an asynchronous GET request to the parse URL."""
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(self.parse_url)
            response.raise_for_status()
            return response.text

    def data_test(self) -> str:
        return """<rates>
    <item>
        <from>USDTTRC20</from>
        <to>CARDRUB</to>
        <in>1</in>
        <out>79.00</out>
        <amount>1000</amount>
        <param>manual</param>
    </item>
    <item>
        <from>CARDRUB</from>
        <to>USDTTRC20</to>
        <in>78.00</in>
        <out>1</out>
        <amount>1000</amount>
        <param>manual</param>
    </item>
    <item>
        <from>BTC</from>
        <to>CARDRUB</to>
        <in>1</in>
        <out>6200000</out>
        <amount>10</amount>
        <param>manual</param>
    </item>
    <item>
        <from>CARDRUB</from>
        <to>BTC</to>
        <in>6100000</in>
        <out>1</out>
        <amount>10</amount>
        <param>manual</param>
    </item>
    <item>
        <from>ETH</from>
        <to>USDTTRC20</to>
        <in>1</in>
        <out>1680</out>
        <amount>5</amount>
        <param>manual</param>
    </item>
    <item>
        <from>USDTTRC20</from>
        <to>ETH</to>
        <in>1680</in>
        <out>1</out>
        <amount>5</amount>
        <param>manual</param>
    </item>
    </rates>"""

    async def parse_xml(self) -> list[str]:
        """
        Parses XML from the parse URL and filters items based on the course value.
        """
        try:
            text = await self.get_request()
            # text = self.data_test()
            return self.parse_xml_text(text)

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code}")
            return []
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            return []
        except ET.ParseError as e:
            logger.error(f"XML parse error: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return []

    def parse_xml_text(self, text: str) -> list[str]:
        """Parses XML from provided text and returns formatted broken-rate messages."""
        root = ET.fromstring(text)

        result = []  # To store the final results
        rates = {}  # To store (from, to) -> price rate

        for item in root.iter('item'):
            from_ = item.find('from').text
            to_ = item.find('to').text

            if from_ in CARDS:
                # From card into crypto: price = in (how many cryptos we get for 1 ruble)
                price = float(item.find('in').text)
            else:
                # From crypto into card: price = out (how many rubles we get for 1 crypto)
                price = float(item.find('out').text)

            rates[(from_, to_)] = price

        checked = set()  # To avoid duplicate checks
        for (from_, to_), price in rates.items():
            if (from_, to_) in checked:
                continue

            reverse_key = (to_, from_)
            if reverse_key in rates:
                reverse_out = rates[reverse_key]
                checked.add((from_, to_))
                checked.add(reverse_key)

                if from_ in CARDS:
                    # from_ = карта (рубли), to_ = крипта
                    card = from_
                    crypto = to_
                    rub_to_crypto = price
                    crypto_to_rub = reverse_out
                elif to_ in CARDS:
                    # from_ = крипта, to_ = карта (рубли)
                    card = to_
                    crypto = from_
                    rub_to_crypto = reverse_out
                    crypto_to_rub = price
                else:
                    continue

                # Rub->Crypto should be greater; otherwise rate is broken.
                if rub_to_crypto <= crypto_to_rub:
                    diff = rub_to_crypto - crypto_to_rub
                    result.append(
                        "\n".join([
                            f"‼️<b>Курс сломан: {crypto} - {card}</b>",
                            f"{card} → {crypto} ({rub_to_crypto:.4f})",
                            "&lt;",
                            f"{crypto} → {card} ({crypto_to_rub:.4f})",
                            f"<b>разница: {rub_to_crypto:.4f} - {crypto_to_rub:.4f} = {diff:.4f}</b>",
                        ])
                    )
            else:
                logger.debug(f"No reverse pair for {from_} → {to_}")

        if result:
            logger.info(f"Found {len(result)} broken pairs")
        else:
            logger.info("No matching broken pairs found")

        return result


parse_service = ParseService()
