from datetime import datetime
from enum import Enum
from typing import List, Optional
import uuid

from sqlalchemy import (
    CheckConstraint,
    Date,
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
from sqlalchemy.types import Enum as SQLEnum


class PlayerCategory(Enum):
    HERREN = "Herren"
    DAMEN = "Damen"
    JUNIOREN = "Junioren"
    SENIOR = "Senioren"
    UNBEKANNT = "Unbekannt"


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


class Organisation(BaseModel):
    """Represents an overarching organisation in the foosball hierarchy."""

    __tablename__ = "organisations"

    name: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False,
        init=False,
        default="Bayerischer Tischfußballverband e.V.",
    )
    acronym: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False,
        init=False,
        default="BTFV",
    )

    # Relationships
    associations: Mapped[List["Association"]] = relationship(
        "Association",
        back_populates="organisation",
        cascade="all, delete-orphan",
        init=False,
    )


class Association(BaseModel):
    """Represents an association that belongs to an organisation."""

    __tablename__ = "associations"

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organisations.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False,
    )

    # Relationships
    organisation: Mapped["Organisation"] = relationship(
        "Organisation", back_populates="associations", init=False
    )
    teams: Mapped[List["Team"]] = relationship(
        "Team", back_populates="association", init=False
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
    is_borrowed: Mapped[bool] = mapped_column(
        default=False, nullable=False, server_default="false"
    )  # Track if the player is being borrowed

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
    category: Mapped[PlayerCategory | None] = mapped_column(
        SQLEnum(PlayerCategory, values_callable=lambda x: [i.value for i in x]),
        nullable=True,
        index=True,
    )
    # Combined rating
    current_mu_combined: Mapped[float] = mapped_column(
        Float, nullable=False, index=True
    )
    current_sigma_combined: Mapped[float] = mapped_column(
        Float, nullable=False, index=True
    )
    # Singles-only rating
    current_mu_singles: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    current_sigma_singles: Mapped[float] = mapped_column(
        Float, nullable=False, index=True
    )
    # Doubles-only rating
    current_mu_doubles: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    current_sigma_doubles: Mapped[float] = mapped_column(
        Float, nullable=False, index=True
    )

    national_id: Mapped[str | None] = mapped_column(String, nullable=True)
    international_id: Mapped[str | None] = mapped_column(String, nullable=True)
    DTFB_from_id: Mapped[str | None] = mapped_column(Integer, nullable=True)
    image_file_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)

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

    __table_args__ = (
        Index(
            "ix_players_name_mu_combined_singles_doubles",  # Index name
            "name",
            "current_mu_combined",
            "current_mu_singles",
            "current_mu_doubles",
        ),
    )


class Team(BaseModel):
    """Represents a team in the foosball division."""

    __tablename__ = "teams"

    name: Mapped[str] = mapped_column(String, nullable=False, index=True)

    division_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("divisions.id"), nullable=False, index=True
    )
    association_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("associations.id"), nullable=False, index=True
    )

    # Relationships
    association: Mapped["Association"] = relationship(
        "Association", back_populates="teams", init=False
    )
    division: Mapped["Division"] = relationship(
        "Division", back_populates="teams", init=False
    )
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


class Division(BaseModel):
    """Represents a division in the foosball league."""

    __tablename__ = "divisions"

    name: Mapped[DivisionName] = mapped_column(
        SQLEnum(DivisionName, values_callable=lambda x: [i.value for i in x]),
        nullable=False,
    )
    hierarchy: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    region: Mapped[str] = mapped_column(
        String,
        nullable=True,
        index=True,
    )

    # Relationships
    teams: Mapped[List["Team"]] = relationship(
        "Team", back_populates="division", cascade="all, delete-orphan", init=False
    )
    season_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("seasons.id"), nullable=False
    )
    season: Mapped["Season"] = relationship(
        "Season", back_populates="divisions", init=False
    )

    __table_args__ = (
        UniqueConstraint(
            "name", "hierarchy", "region", "season_id", name="uq_division"
        ),
        Index("idx_hierarchy_region", "hierarchy", "region"),
    )


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
    BTFV_from_id: Mapped[int] = mapped_column(Integer, nullable=False)

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
