"""Pydantic models for all Wilma API responses and domain objects."""

from __future__ import annotations

import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class RoleType(StrEnum):
    teacher = "teacher"
    student = "student"
    personnel = "personnel"
    guardian = "guardian"
    workplaceinstructor = "workplaceinstructor"
    board = "board"
    passwd = "passwd"
    trainingcoordinator = "trainingcoordinator"
    training = "training"
    applicant = "applicant"
    applicantguardian = "applicantguardian"


# ---------------------------------------------------------------------------
# Server discovery
# ---------------------------------------------------------------------------


class Municipality(BaseModel):
    name_fi: str
    name_sv: str


class WilmaServer(BaseModel):
    url: str
    name: str
    former_url: str | None = Field(None, alias="formerUrl")
    municipalities: list[Municipality] = []

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Session init
# ---------------------------------------------------------------------------


class SessionInit(BaseModel):
    """Response from GET /index_json (before login)."""

    login_result: str = Field(alias="LoginResult")
    session_id: str = Field(alias="SessionID")
    api_version: int = Field(alias="ApiVersion")

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------------


class School(BaseModel):
    id: int
    caption: str
    features: list[str] = []


class AccountRole(BaseModel):
    """Raw role as returned by /api/v1/accounts/me/roles."""

    name: str
    type: str
    primus_id: int = Field(alias="primusId")
    form_key: str = Field(alias="formKey")
    slug: str
    schools: list[School] = []

    model_config = {"populate_by_name": True}


class AccountInfo(BaseModel):
    """Raw account info from /api/v1/accounts/me."""

    id: int
    firstname: str
    lastname: str
    username: str
    last_login: str = Field(alias="lastLogin")
    sessions: list[Any] = []
    multi_factor_authentication: bool = Field(False, alias="multiFactorAuthentication")

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Domain: Role (normalised)
# ---------------------------------------------------------------------------


class Role(BaseModel):
    name: str
    type: RoleType
    id: int
    is_default: bool
    slug: str
    form_key: str


# ---------------------------------------------------------------------------
# Domain: Account (normalised session account)
# ---------------------------------------------------------------------------


class Account(BaseModel):
    id: int
    firstname: str
    lastname: str
    username: str
    last_login: datetime.datetime | None = None


# ---------------------------------------------------------------------------
# Schedule
# ---------------------------------------------------------------------------


class Teacher(BaseModel):
    id: int = Field(alias="kortti")
    account_id: str = Field(alias="tunniste")
    callsign: str = Field(alias="lyhenne")
    name: str = Field(alias="nimi")

    model_config = {"populate_by_name": True}


class Room(BaseModel):
    id: str = Field(alias="kortti")
    short_name: str = Field(alias="lyhenne")
    name: str = Field(alias="nimi")

    model_config = {"populate_by_name": True}


class ScheduleEventDate(BaseModel):
    start: datetime.datetime
    end: datetime.datetime
    length_minutes: int


class ScheduleEventDetails(BaseModel):
    info: str
    notes: list[str]
    teachers: list[Teacher]
    rooms: list[Room]
    vvt: str
    creator: str | None
    editor: str | None
    visible: bool


class ScheduleEvent(BaseModel):
    id: int
    date: ScheduleEventDate
    short_name: str
    name: str
    color: str
    details: ScheduleEventDetails


class Term(BaseModel):
    name: str
    start_date: datetime.datetime
    end_date: datetime.datetime


class Schedule(BaseModel):
    events: list[ScheduleEvent]
    terms: list[Term]
