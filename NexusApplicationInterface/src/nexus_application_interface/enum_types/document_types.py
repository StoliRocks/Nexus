from enum import Enum, unique


# Document enum_types supported by Nexus
@unique
class DocumentType(Enum):
    PDF = "PDF"
    TXT = "TXT"
    MD = "MD"
    # Add more document enum_types as needed


@unique
class DocumentFrameworkType(Enum):
    AWS = "AWS"
    INDUSTRY = "INDUSTRY"
