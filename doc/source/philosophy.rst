.. TyphoonAE philosophy.

The philosophy behind TyphoonAE
===============================

The Google App Engine SDK delivers a development web server that mirrors the
production environment near flawlessly. But you obviously can't use that in a
real production environment. That's where TyphoonAE comes in. It is the missing
link to build a full-featured and productive serving environment to run Google
App Engine (Python) applications. The main principles in the design of
TyphoonAE are decoupling and statelessness to provide concurrency, better
caching, horizontal scalability and fault-tolerance. It integrates various open
source products where each one is a superhero and scales independently.

Furthermore, TyphoonAE aims at staying as modular as possible. It goes without
patching the SDK and utilizes the same dependency injection 'stub' pattern. So,
it has an astonishing small code base with good test coverage.
