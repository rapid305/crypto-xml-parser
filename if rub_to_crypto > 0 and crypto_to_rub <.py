if rub_to_crypto > 0 and crypto_to_rub < rub_to_crypto:
                    diff = rub_to_crypto - crypto_to_rub
                    percentage_diff = (diff / rub_to_crypto) * 100
                    
                    # Alert only if difference is less than 0.5%
                    if percentage_diff < 0.5:
                        result.append(
                            "\n".join([
                                f"⚠️<b>Курс близкий: {crypto} - {card}</b>",
                                f"{card} → {crypto} ({rub_to_crypto:.4f})",
                                f"{crypto} → {card} ({crypto_to_rub:.4f})",
                                f"<b>разница: {diff:.4f} ({percentage_diff:.2f}%)</b>",
                            ])
                        )