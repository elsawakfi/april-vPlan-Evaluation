import re

# ==========================================================
# SECTION AND HEADING PATTERNS
# ==========================================================


SECTION_REGEX = re.compile(
    r'^((?:\d+(?:\.\d+)*|[A-C]\d+(?:\.\d+)*))\s+(.+)$'
)

VALID_VPLAN_SECTION_REGEX = re.compile(
    r'^(?:[A-C]\d+(?:\.\d+)*)$'
)

# ==========================================================
# TABLE PATTERNS
# ==========================================================

TABLE_REGEX = re.compile(
    r'(Table)\s+([A-Za-z]?\d+(?:[-.]\d+)*)',
    re.IGNORECASE
)

TABLE_REF_REGEX = re.compile(
    r'Table\s+[A-Za-z]?\d+(?:[-.]\d+)*',
    re.IGNORECASE
)

# ==========================================================
# REQUIREMENT PATTERNS
# ==========================================================

REQ_ID_REGEX = re.compile(
    r'([A-Z_]*REQ[-_]?\d+)',
    re.IGNORECASE
)

FEATURE_REGEX = re.compile(
    r'\b('
    r'to transfer|'
    r'permits|'
    r'supports|'
    r'provides|'
    r'contains|'
    r'uses|'
    r'controls|'
    r'control|'
    r'can either|'
    r'can pass|'
    r'requires that|'
    r'perform'
    r')\b',
    re.IGNORECASE
)

REQUIREMENT_REGEX = re.compile(
    r'\b('
    #strong obligations / prohubitions
    r'shall|shall not|'
    r'require|required|'
    r'permitted|'
    r'able to|'
    r'specified|not specified|'
    r'must|must not|'
    r'must have|must not have|must be|must not be|'
    r'must issue|must not issue|'
    r'length can be|'
    r'can discard|'
    r'must complete|must not complete|'
    r'must be consistent|'
    r'must not cross|'
    r'should|should not|'
    r'cannot|can not|'
    r'can omit|'
    r'is required to|are required to|required to|'
    r'is prohibited|are prohibited|prohibited to|'
    r'is not allowed to|are not allowed to|not allowed to|'
    r'is not permitted to|are not permitted to|not permitted to|'
    r'are non-modifiable| is non-modifiable|'
    r'are nonmodifiable| is nonmodifiable|'
    r'is not present|are not present|'
    r'must be able to|must be given|'
    r'is indicated|are indicated|'
    r'is issued|are issued|'
    r'is sent|are sent|'
    r'is determined|are determined|'
    r'is returned|are returned|'
    r'is terminated|are terminated|'
    r'returns|'
    r'is sent|'

    #Timing / protocol behaviour
    r'must remain|shall remain|remain asserted|remains asserted|'
    r'must be held|must be stable|'
    r'must be stable|shall be stable|remain stable|'
    r'shall be asserted|must be asserted|'
    r'shall be deasserted|must be deasserted|'

    #Validity / legality constraints
    r'is valid only when|are valid only when|'
    r'is not valid|are not valid|'
    r'is only valid|are only valid|'
    r'can only be|may only be|'
    r'is not satisfied|are not satisfied|'
    r'is satisfied|are satisfied|'

    #Optional / supported behaviour 
    r'is not supported|are not supported|'
    r'is supported|are supported|'
    r'is optional|are optional|'

    #Legal values / bounds
    r'can be lower than|can be higher than|'
    r'can be up to|may be up to|'
    r'can range from|may range from|'
    r'can be obtained|'

    #Spec-specific but common protocol phrasing
    r'early termination of .* not supported|' # .* means anything in between.
    r'is half that specified by|'
    r'is determined from|'

    #extra keywords
    r'permitted to|is permitted to|are permitted to|'
    r'is permitted|are permitted|'
    r'allowed to|is allowed to|are allowed to|'
    r'can be asserted|can be deasserted|'
    r'may be asserted|may be deasserted|'
    r'may not'
    r'are present|are not present|is present|is not present|'
    r'is deasserted|are deasserted|is asserted|are asserted|' \
    r'can be sent|'
    r'indicates that|'
    
    r')\b',
    re.IGNORECASE
)

# ==========================================================
# NOTE AND ACRONYM PATTERNS
# ==========================================================

NOTE_REGEX = re.compile(
    r'^(NOTE|WARNING|CAUTION|IMPORTANT|ASSUMPTION)\b',
    re.IGNORECASE
)

ACRONYM_REGEX = re.compile(
    r'\b([A-Z]{2,10})\b'
)

# ==========================================================
# CROSS-REFERENCE PATTERNS
# ==========================================================

SECTION_REF_REGEX = re.compile(
    r'Section\s+\d+(?:\.\d+)*',
    re.IGNORECASE
)


# ==========================================================
# ENCODING TABLE PATTERN
# ==========================================================


ENCODING_TABLE_REGEX = re.compile(
    r'(0b[01]+)\s+'
    r'([A-Za-z][A-Za-z0-9_-]*)\s+'
    r'(.*?)'
    r'(?='
        r'\s+0b[01]+\s+[A-Za-z][A-Za-z0-9_-]*\s+'
        r'|'
        r'\s+(?:\d+(?:\.\d+)*|[A-C]\d+(?:\.\d+)*)\s+'
        r'|'
        r'\s+Table\s+[A-Za-z]?\d+'
        r'|$'
    r')',
    re.DOTALL
)