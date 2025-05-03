# type: ignore
import pandas as pd


def prepare_match_data(
    matches: list[dict[str, str | int | None]], player_name: str
) -> pd.DataFrame:
    data = {
        "date": [],
        "mu_after": [],
        "sigma_after": [],
        "confident_mu": [],
        "mu_upper": [],
        "mu_lower": [],
        "global_match_nr": [],
        "mu_gain": [],
    }

    for m in matches:
        # Filter
        if m["home_player_name"] == player_name or m["away_player_name"] == player_name:
            # Felder lesen
            date = m["date"]
            if m["home_player_name"] == player_name:
                mu_after = m["home_mu_after"]
                sigma_after = m["home_sigma_after"]
            else:
                mu_after = m["away_mu_after"]
                sigma_after = m["away_sigma_after"]

            confident_mu = mu_after - 3 * sigma_after
            mu_upper = mu_after + sigma_after
            mu_lower = mu_after - sigma_after
            global_nr = m["global_match_nr"]
            mu_gain = m.get("mu_gain", 0.0)

            # anhängen
            data["date"].append(date)
            data["mu_after"].append(mu_after)
            data["sigma_after"].append(sigma_after)
            data["confident_mu"].append(confident_mu)
            data["mu_upper"].append(mu_upper)
            data["mu_lower"].append(mu_lower)
            data["global_match_nr"].append(global_nr)
            data["mu_gain"].append(mu_gain)

    df = pd.DataFrame(data)

    # Now we group by the date and select the last match
    df = df.sort_values("date").drop_duplicates(subset="date", keep="last")
    df["delta_mu"] = df["confident_mu"].diff()
    # erste Zeile statt NaN mit 0 füllen
    df["delta_mu"].fillna(0, inplace=True)

    return df
