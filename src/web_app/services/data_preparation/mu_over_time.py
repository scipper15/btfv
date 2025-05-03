# type: ignore
import pandas as pd


def prepare_match_data(
    matches: list[dict[str, str | int | None]], player_name: str
) -> pd.DataFrame:
    data: dict[str, list[str | float]] = {
        "date": [],
        "mu_after": [],
        "sigma_after": [],
        "confident_mu": [],
        "mu_upper": [],
        "mu_lower": [],
        "global_match_nr": [],
    }

    # Filter out matches for the specific player
    for match in matches:
        if (
            match.home_player_name == player_name
            or match.away_player_name == player_name
        ):
            match_date = match.date
            mu_after = (
                match.home_mu_after
                if match.home_player_name == player_name
                else match.away_mu_after
            )
            sigma_after = (
                match.home_sigma_after
                if match.home_player_name == player_name
                else match.away_sigma_after
            )
            confident_mu = mu_after - 3 * sigma_after

            # Compute upper and lower bounds for varea
            mu_upper = mu_after + sigma_after
            mu_lower = mu_after - sigma_after

            # Append data to lists
            data["date"].append(match_date)
            data["mu_after"].append(mu_after)
            data["sigma_after"].append(sigma_after)
            data["confident_mu"].append(confident_mu)
            data["mu_upper"].append(mu_upper)
            data["mu_lower"].append(mu_lower)
            data["global_match_nr"].append(
                match.global_match_nr
            )  # Adding global match nr

    # Convert to pandas DataFrame
    df = pd.DataFrame(data)

    # Now we group by the date and select the last match
    df = df.sort_values("date").drop_duplicates(subset="date", keep="last")
    df["delta_mu"] = df["confident_mu"].diff()
    # erste Zeile statt NaN mit 0 füllen
    df["delta_mu"].fillna(0, inplace=True)

    return df
