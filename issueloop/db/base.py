
from abc import ABC, abstractmethod
from typing import Optional

from ..agent_state import Ticket


class TicketStoreBackend(ABC):
    @abstractmethod
    def create_ticket(self, ticket: Ticket): ...

    @abstractmethod
    def update_ticket(self, ticket_id: str, **fields): ...

    @abstractmethod
    def get_open_tickets(self, repo: Optional[str] = None): ...

    @abstractmethod
    def dispense_next(self, repo: Optional[str] = None):...

    @abstractmethod
    def purge_old(self, older_than_days: int, repo: Optional[str] = None):...
