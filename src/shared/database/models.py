from datetime import datetime
from enum import Enum
from typing import List, Optional
import uuid

from sqlalchemy import (
    CheckConstraint,
    Date,
    Enum as SqlEnum,
    Float,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    MappedAsDataclass,
    mapped_column,
    relationship,
)


class PlayerCategory(Enum):
    JUNIOR = "Junior"
    SENIOR = "Senior"


class DivisionName(Enum):
    LANDESLIGA = "Landesliga"
    VERBANDSLIGA = "Verbandsliga"
    BEZIRKSLIGA = "Bezirksliga"
    KREISLIGA = "Kreisliga"


class BaseModel(MappedAsDataclass, DeclarativeBase):
    """Abstract base class for all models, providing common fields."""

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, init=False
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        init=False,
    )
    modified_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        init=False,
    )


class TeamMembership(BaseModel):
    """Association table linking Players to Teams for specific Seasons."""

    __tablename__ = "team_memberships"
    player_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("players.id"), primary_key=True
    )
    team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("teams.id"), primary_key=True)
    season_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("seasons.id"), primary_key=True
    )

    # Relationships
    player: Mapped["Player"] = relationship(
        "Player", back_populates="team_memberships", init=False
    )
    team: Mapped["Team"] = relationship(
        "Team", back_populates="team_memberships", init=False
    )
    season: Mapped["Season"] = relationship(
        "Season", back_populates="team_memberships", init=False
    )


class Player(BaseModel):
    """Represents a player in the foosball division."""

    __tablename__ = "players"

    name: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    birth_name: Mapped[Optional[str]] = mapped_column(
        String, unique=True, nullable=True, index=True, init=False
    )
    category: Mapped[PlayerCategory] = mapped_column(
        SqlEnum(PlayerCategory), nullable=True, index=True, init=False
    )
    current_mu: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    current_sigma: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    national_id: Mapped[str] = mapped_column(
        String, unique=True, nullable=True, index=True, init=False
    )
    international_id: Mapped[Optional[str]] = mapped_column(
        String, unique=True, nullable=True, index=True, init=False
    )
    organisation: Mapped[str] = mapped_column(  # always the same: BTFV
        String,
        nullable=False,
        index=True,
        init=False,
        default="Bayerischer Tischfußballverband e.V.",
    )
    association: Mapped[str] = mapped_column(
        String, unique=True, nullable=True, index=True, init=False
    )

    # Relationships
    team_memberships: Mapped[List["TeamMembership"]] = relationship(
        "TeamMembership",
        back_populates="player",
        cascade="all, delete-orphan",
        init=False,
    )
    matches: Mapped[List["MatchParticipant"]] = relationship(
        "MatchParticipant",
        back_populates="player",
        cascade="all, delete-orphan",
        init=False,
    )

    __table_args__ = (Index("ix_players_name_mu", "name", "current_mu"),)


class Team(BaseModel):
    """Represents a team in the foosball division."""

    __tablename__ = "teams"

    name: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)

    division_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("divisions.id"), nullable=False, index=True
    )

    # Relationships
    team_memberships: Mapped[List["TeamMembership"]] = relationship(
        "TeamMembership",
        back_populates="team",
        cascade="all, delete-orphan",
        init=False,
    )
    home_matches: Mapped[List["Match"]] = relationship(
        "Match",
        back_populates="home_team",
        foreign_keys="Match.home_team_id",
        init=False,
    )
    away_matches: Mapped[List["Match"]] = relationship(
        "Match",
        back_populates="away_team",
        foreign_keys="Match.away_team_id",
        init=False,
    )
    # Define relationship back to Division
    division: Mapped["Division"] = relationship(
        "Division", back_populates="teams", init=False
    )


class Division(BaseModel):
    """Represents a division in the foosball league."""

    __tablename__ = "divisions"

    name: Mapped[DivisionName] = mapped_column(
        SqlEnum(DivisionName), nullable=False, index=True
    )
    hierarchy: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    region: Mapped[str] = mapped_column(String, nullable=True, index=True)

    # Relationships
    teams: Mapped[List["Team"]] = relationship(
        "Team", back_populates="division", cascade="all, delete-orphan", init=False
    )
    season_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("seasons.id"), nullable=False, index=True
    )
    season: Mapped["Season"] = relationship(
        "Season", back_populates="divisions", init=False
    )

    __table_args__ = (Index("ix_divisions_name_hierarchy", "name", "hierarchy"),)


class Season(BaseModel):
    """Represents a season in the foosball league."""

    __tablename__ = "seasons"

    season_year: Mapped[int] = mapped_column(
        Integer, unique=True, nullable=False, index=True
    )

    # Relationships
    divisions: Mapped[List["Division"]] = relationship(
        "Division", back_populates="season", cascade="all, delete-orphan", init=False
    )
    team_memberships: Mapped[List["TeamMembership"]] = relationship(
        "TeamMembership",
        back_populates="season",
        cascade="all, delete-orphan",
        init=False,
    )
    matches: Mapped[List["Match"]] = relationship(
        "Match", back_populates="season", cascade="all, delete-orphan", init=False
    )


class Match(BaseModel):
    """Represents a match between two teams in a specific season."""

    __tablename__ = "matches"

    global_match_nr: Mapped[int] = mapped_column(
        Integer, Identity(start=1), nullable=False, index=True, init=False
    )
    match_nr: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    match_day_nr: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    draw_probability: Mapped[float] = mapped_column(Float, nullable=False)
    win_probability: Mapped[float] = mapped_column(Float, nullable=False)
    sets_home: Mapped[int] = mapped_column(Integer, nullable=False)
    sets_away: Mapped[int] = mapped_column(Integer, nullable=False)
    who_won: Mapped[str] = mapped_column(
        String, nullable=False, index=True
    )  # 'home', 'away', 'draw'
    match_type: Mapped[str] = mapped_column(
        String, nullable=False, index=True
    )  # 'single', 'double'

    home_team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id"), nullable=False, index=True
    )
    away_team_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teams.id"), nullable=False, index=True
    )
    season_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("seasons.id"), nullable=False, index=True
    )

    # Relationships
    home_team: Mapped["Team"] = relationship(
        "Team", foreign_keys=[home_team_id], back_populates="home_matches", init=False
    )
    away_team: Mapped["Team"] = relationship(
        "Team", foreign_keys=[away_team_id], back_populates="away_matches", init=False
    )
    season: Mapped["Season"] = relationship(
        "Season", back_populates="matches", init=False
    )
    participants: Mapped[List["MatchParticipant"]] = relationship(
        "MatchParticipant",
        back_populates="match",
        cascade="all, delete-orphan",
        init=False,
    )

    __table_args__ = (
        UniqueConstraint("global_match_nr", "season_id", name="uq_global_match_season"),
        CheckConstraint("sets_home >= 0 AND sets_home <= 2", name="check_sets_home"),
        CheckConstraint("sets_away >= 0 AND sets_away <= 2", name="check_sets_away"),
    )


class MatchParticipant(BaseModel):
    """Association Table representing the participation of a player in a match."""

    __tablename__ = "match_participants"

    match_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("matches.id"), nullable=False, index=True
    )
    player_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("players.id"), nullable=False, index=True
    )
    team_side: Mapped[str] = mapped_column(String, nullable=False)  # 'home' or 'away'

    # Player's rating before and after the match
    mu_before: Mapped[float] = mapped_column(Float, nullable=False)
    sigma_before: Mapped[float] = mapped_column(Float, nullable=False)
    mu_after: Mapped[float] = mapped_column(Float, nullable=False)
    sigma_after: Mapped[float] = mapped_column(Float, nullable=False)

    # Relationships
    match: Mapped["Match"] = relationship(
        "Match", back_populates="participants", init=False
    )
    player: Mapped["Player"] = relationship(
        "Player", back_populates="matches", init=False
    )