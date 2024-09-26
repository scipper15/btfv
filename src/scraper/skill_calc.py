import itertools
import math
from typing import List, Tuple

import trueskill  # type: ignore


class SkillCalc:
    def __init__(
        self,
        mu: float = 25.0,
        sigma: float = 8.333,
        beta: float = 4.1667,
        tau: float = 0.083333,
        draw_probability: float = 0.0,
    ) -> None:
        # Initialize the TrueSkill environment with the provided parameters
        self.env = trueskill.TrueSkill(
            mu=mu, sigma=sigma, beta=beta, tau=tau, draw_probability=draw_probability
        )
        self.mu = mu
        self.sigma = sigma
        self.beta = beta
        self.tau = tau
        self.draw_probability = draw_probability

    def rate_single_match(
        self,
        player1_rating: trueskill.Rating,
        player2_rating: trueskill.Rating,
        winner: str,
    ) -> Tuple[trueskill.Rating, trueskill.Rating]:
        """Adjust ratings based on a singles match outcome."""
        if winner == "draw":
            new_rating1, new_rating2 = self.env.rate_1vs1(
                player1_rating, player2_rating, drawn=True
            )
        elif winner == "player1":
            new_rating1, new_rating2 = self.env.rate_1vs1(
                player1_rating, player2_rating
            )
        else:  # winner == "player2"
            new_rating2, new_rating1 = self.env.rate_1vs1(
                player2_rating, player1_rating
            )

        return new_rating1, new_rating2

    def rate_double_match(
        self,
        team1_ratings: List[trueskill.Rating],
        team2_ratings: List[trueskill.Rating],
        winner: str,
    ) -> Tuple[List[trueskill.Rating], List[trueskill.Rating]]:
        """Adjust ratings based on a doubles match outcome."""
        if winner == "draw":
            new_ratings = self.env.rate(
                [team1_ratings, team2_ratings], ranks=[0, 0]
            )  # Draw
        elif winner == "team1":
            new_ratings = self.env.rate(
                [team1_ratings, team2_ratings], ranks=[0, 1]
            )  # Team1 won
        else:  # winner == "team2"
            new_ratings = self.env.rate(
                [team2_ratings, team1_ratings], ranks=[1, 0]
            )  # Team2 won

        # Unpack the new ratings for each team
        new_team1_ratings, new_team2_ratings = new_ratings

        return new_team1_ratings, new_team2_ratings

    def win_probability(
        self, team1: List[trueskill.Rating], team2: List[trueskill.Rating]
    ) -> float:
        """Calculate the win probability of team1 over team2."""
        delta_mu = sum(r.mu for r in team1) - sum(r.mu for r in team2)
        sum_sigma = sum(r.sigma**2 for r in itertools.chain(team1, team2))
        size = len(team1) + len(team2)
        denom = math.sqrt(size * (self.beta**2) + sum_sigma)
        self.env.cdf(delta_mu / denom)
        return self.env.cdf(delta_mu / denom)

    def create_rating(
        self, mu: float | None = None, sigma: float | None = None
    ) -> trueskill.Rating:
        """Create a new TrueSkill rating for a player."""
        return self.env.Rating(mu=mu or self.mu, sigma=sigma or self.sigma)
