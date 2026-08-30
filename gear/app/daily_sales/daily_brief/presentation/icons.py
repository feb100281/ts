# gear/app/daily_sales/daily_brief/presentation/icons.py
from __future__ import annotations

# Все иллюстрации локальные SVG: PDF не зависит от интернета, JS и CDN.
ICONS = {
    "newspaper": '<svg viewBox="0 0 64 64"><path fill="#FFD84D" stroke="#14213D" stroke-width="2" d="M8 10h48v44H8z"/><path fill="#14213D" d="M14 17h36v7H14zm0 13h15v18H14zm20 0h16v4H34zm0 8h16v4H34zm0 8h11v3H34z"/></svg>',
    "revenue": '<svg viewBox="0 0 64 64"><path fill="#FF78A5" stroke="#14213D" stroke-width="2" d="M8 16h48v34H8z"/><circle cx="32" cy="33" r="9" fill="#FFD84D" stroke="#14213D" stroke-width="2"/><path d="M14 24h5m26 18h5" stroke="#14213D" stroke-width="3"/></svg>',
    "units": '<svg viewBox="0 0 64 64"><path fill="#9BFF57" stroke="#14213D" stroke-width="2" d="M12 23h40l-4 34H16z"/><path d="M23 25v-7a9 9 0 0 1 18 0v7" fill="none" stroke="#14213D" stroke-width="3"/></svg>',
    "returns": '<svg viewBox="0 0 64 64"><path d="M24 18 10 32l14 14" fill="none" stroke="#14213D" stroke-width="5"/><path d="M12 32h27c9 0 15 5 15 14" fill="none" stroke="#FF78A5" stroke-width="7"/></svg>',
    "margin": '<svg viewBox="0 0 64 64"><path fill="#E9EDF1" d="M8 50h48v6H8z"/><path fill="#FFD84D" stroke="#14213D" stroke-width="2" d="M13 37h8v13h-8zm15-12h8v25h-8zm15-16h8v41h-8z"/><path d="m12 31 15-13 11 8 15-17" fill="none" stroke="#FF78A5" stroke-width="3"/></svg>',
    "calendar": '<svg viewBox="0 0 64 64"><path fill="#FFD84D" stroke="#14213D" stroke-width="2" d="M9 14h46v42H9z"/><path fill="#14213D" d="M9 14h46v11H9z"/><g fill="#FF78A5"><circle cx="20" cy="35" r="4"/><circle cx="32" cy="35" r="4"/><circle cx="44" cy="35" r="4"/><circle cx="20" cy="47" r="4"/><circle cx="32" cy="47" r="4"/></g></svg>',
    "price": '<svg viewBox="0 0 64 64"><path fill="#9BFF57" stroke="#14213D" stroke-width="2" d="M10 12h30l14 14-28 28L10 38z"/><circle cx="29" cy="26" r="5" fill="#FFF" stroke="#14213D" stroke-width="2"/><path d="M20 43 44 19" stroke="#14213D" stroke-width="3"/></svg>',
    "brand": '<svg viewBox="0 0 64 64"><path fill="#FF78A5" stroke="#14213D" stroke-width="2" d="m32 6 7 8 11-1 2 11 9 6-6 9 2 11-11 2-6 9-8-7-10 7-6-9-11-2 2-11-6-9 9-6 2-11 11 1z"/><path d="m21 33 7 7 15-17" fill="none" stroke="#FFF" stroke-width="4"/></svg>',
    "category": '<svg viewBox="0 0 64 64"><g stroke="#14213D" stroke-width="2"><path fill="#FFD84D" d="M8 8h20v20H8z"/><path fill="#FF78A5" d="M36 8h20v20H36z"/><path fill="#9BFF57" d="M8 36h20v20H8z"/><path fill="#FFF" d="M36 36h20v20H36z"/></g></svg>',
    "stock": '<svg viewBox="0 0 64 64"><path fill="#9BFF57" stroke="#14213D" stroke-width="2" d="M7 20 32 7l25 13v27L32 59 7 47z"/><path d="m7 20 25 13 25-13M32 33v26" fill="none" stroke="#14213D" stroke-width="3"/></svg>',
    "truck": '<svg viewBox="0 0 64 64"><path fill="#FFD84D" stroke="#14213D" stroke-width="2" d="M5 17h34v28H5z"/><path fill="#FF78A5" stroke="#14213D" stroke-width="2" d="M39 27h12l8 9v9H39z"/><g fill="#14213D"><circle cx="18" cy="48" r="6"/><circle cx="49" cy="48" r="6"/></g></svg>',
    "map": '<svg viewBox="0 0 64 64"><path fill="#FFD84D" stroke="#14213D" stroke-width="2" d="m8 13 15-6 18 7 15-6v43l-15 6-18-7-15 6z"/><path d="M23 7v43m18-36v43" stroke="#14213D" stroke-width="2"/><circle cx="34" cy="28" r="7" fill="#FF78A5" stroke="#14213D" stroke-width="2"/></svg>',
    "plan": '<svg viewBox="0 0 64 64"><path fill="#FFF" stroke="#14213D" stroke-width="2" d="M13 7h38v50H13z"/><path fill="#FFD84D" d="M19 15h26v7H19z"/><path d="m20 35 7 7 17-18" fill="none" stroke="#9AD94E" stroke-width="5"/></svg>',
    "focus": '<svg viewBox="0 0 64 64"><circle cx="32" cy="32" r="25" fill="#FFD84D" stroke="#14213D" stroke-width="2"/><circle cx="32" cy="32" r="14" fill="#FFF" stroke="#14213D" stroke-width="2"/><circle cx="32" cy="32" r="5" fill="#FF78A5"/></svg>',
    "fire": """ <svg viewBox="0 0 64 64"><path d="M34 5
                   C37 16 29 19 34 27
                   C39 23 42 18 41 13
                   C52 22 57 32 53 44
                   C50 54 42 60 31 60
                   C18 60 9 51 9 39
                   C9 29 15 21 24 14
                   C23 23 27 26 30 27
                   C28 19 30 11 34 5Z"
                fill="#E85D75"
                stroke="#14213D"
                stroke-width="2"
                stroke-linejoin="round"
            />

            <path
                d="M32 31
                   C36 37 31 39 35 44
                   C38 41 39 38 39 35
                   C44 40 45 45 43 50
                   C41 55 37 58 31 58
                   C24 58 19 53 19 47
                   C19 41 23 37 27 34
                   C27 39 29 41 31 42
                   C29 38 30 34 32 31Z"
                fill="#FFD84D"
                stroke="#14213D"
                stroke-width="1.5"
            />
        </svg>
    """,

    "snapshot": """
        <svg viewBox="0 0 64 64">
            <circle
                cx="32"
                cy="32"
                r="24"
                fill="#F4F0E6"
                stroke="#14213D"
                stroke-width="2"
            />

            <path
                d="M32 17v16l11 7"
                fill="none"
                stroke="#14213D"
                stroke-width="4"
                stroke-linecap="round"
                stroke-linejoin="round"
            />
        </svg>
    """,
}


def icon(name: str, size: int = 30) -> str:
    svg = ICONS.get(name, ICONS["newspaper"])
    return f'<span class="svg-icon" style="width:{size}px;height:{size}px">{svg}</span>'
