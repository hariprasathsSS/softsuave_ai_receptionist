"""Application layer module.

Use cases (interactors) that orchestrate domain entities to fulfill
business operations. This layer depends ONLY on `domain/`.

Each use case receives its dependencies (repository interfaces,
provider interfaces) via constructor injection — never imports
infrastructure directly.
"""

