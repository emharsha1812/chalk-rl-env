---
hide:
  - navigation
  - toc
---

<div class="chalk-home">
<section class="hero">
  <div class="site-shell hero-inner">
    <nav class="site-nav" aria-label="Main navigation">
      <a class="site-brand" href="/__chalk_home__/" aria-label="Chalk home"><img src="assets/chalk-logo.png" alt="Chalk"></a>
      <span class="nav-caption">AN OPEN-SOURCE RL FRAMEWORK</span>
      <a class="nav-link" href="/__chalk_docs__/">DOCUMENTATION <span aria-hidden="true">↗</span></a>
    </nav>
    <div class="hero-content">
      <div class="hero-copy">
        <p class="eyebrow"><span aria-hidden="true">+</span> ENVIRONMENTS FOR REASONING</p>
        <h1>Build environments<br><span>for reasoning.</span></h1>
        <p class="lead">Chalk gives agents a place to work. Define a task, provide tools, and check what happened.</p>
        <div class="actions">
          <a class="action action-primary" href="/__chalk_docs__/getting-started/quick-start/">Get started <span aria-hidden="true">→</span></a>
          <a class="action action-secondary" href="/__chalk_docs__/">Read the docs <span aria-hidden="true">→</span></a>
        </div>
        <p class="hero-note">LOCAL FIRST <span>/</span> PYTHON 3.12+ <span>/</span> OPEN SOURCE</p>
      </div>
    </div>
    <div class="hero-bottom">
      <span>CHALK / FIELD GUIDE</span>
      <a href="#anatomy">EXPLORE THE ANATOMY <span aria-hidden="true">↓</span></a>
      <span>01 — 04</span>
    </div>
  </div>
</section>

<section class="anatomy-section site-shell" id="anatomy">
  <div class="section-intro">
    <p class="section-kicker">[ 01 / ANATOMY ]</p>
    <div>
      <h2>Inside an<br>environment<span class="cursor-mark" aria-hidden="true">_</span></h2>
      <p>Click or tap the cube to explore the parts of a Chalk run.</p>
    </div>
  </div>
  <figure class="anatomy-figure" data-expanded="false">
    <div class="figure-heading">
      <span>FIG. 01 <span class="figure-label-detail">/ ANATOMY</span></span>
      <button class="diagram-toggle" type="button" aria-controls="cubeViewport" aria-label="Separate the cube" hidden><span class="toggle-label">Separate</span> <span class="toggle-symbol" aria-hidden="true">[+]</span></button>
    </div>
    <div class="cube-viewport" id="cubeViewport" aria-describedby="cube-hint">
      <svg id="cubeSvg" class="cube-svg" viewBox="0 0 1280 820" preserveAspectRatio="xMidYMid meet" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="cubeHatch" width="6" height="6" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">
            <line x1="0" y1="0" x2="0" y2="6" stroke="var(--stroke-subtle)" stroke-width="0.8" opacity="0.42" />
          </pattern>
          <marker id="cubeCalloutDot" viewBox="0 0 8 8" refX="4" refY="4" markerWidth="5" markerHeight="5">
            <circle cx="4" cy="4" r="2.6" fill="var(--stroke-main)" />
          </marker>
        </defs>
        <g id="cubeAxisUnderlay"></g>
        <g id="cubeLayers"></g>
        <g id="cubeAxisOverlay"></g>
        <g id="cubeCallouts"></g>
      </svg>
      <noscript><p class="cube-fallback">Enable JavaScript to explore the cube. The parts are listed below.</p></noscript>
    </div>
    <ol class="cube-mobile-labels" aria-label="Parts of the environment">
      <li><span>01</span> Observations</li>
      <li><span>02</span> Agent</li>
      <li><span>03</span> Task</li>
      <li><span>04</span> Judge</li>
      <li><span>05</span> Tools</li>
      <li><span>06</span> Data</li>
      <li><span>07</span> Workspace</li>
      <li><span>08</span> Runtime</li>
    </ol>
    <figcaption class="figure-footer">
      <span id="cube-hint">Click or tap · Drag to rotate · Arrow keys</span>
      <span id="cube-status" aria-live="polite">Cube assembled</span>
    </figcaption>
  </figure>
  <details class="cube-key">
    <summary>ABOUT THE PARTS <span aria-hidden="true">+</span></summary>
    <ol>
      <li><span>01</span><div><strong>Observations</strong><p>Messages and tool results the agent receives.</p></div></li>
      <li><span>02</span><div><strong>Agent</strong><p>Uses a model to work through the task.</p></div></li>
      <li><span>03</span><div><strong>Task</strong><p>The instructions and steps to work on.</p></div></li>
      <li><span>04</span><div><strong>Judge</strong><p>Checks the work and returns a score.</p></div></li>
      <li><span>05</span><div><strong>Tools</strong><p>Actions available to the agent.</p></div></li>
      <li><span>06</span><div><strong>Data</strong><p>Files and inputs used by the task.</p></div></li>
      <li><span>07</span><div><strong>Workspace</strong><p>The isolated place where a run works.</p></div></li>
      <li><span>08</span><div><strong>Runtime</strong><p>Runs the sandbox in a container or virtual machine.</p></div></li>
    </ol>
    <a class="inline-link" href="/__chalk_docs__/getting-started/concepts/">EXPLORE THE CONCEPTS <span aria-hidden="true">↗</span></a>
  </details>
</section>

<section class="workflow-section site-shell">
  <div class="section-intro compact-intro">
    <p class="section-kicker">[ 02 / THE WORKFLOW ]</p>
    <div><h2>From task<br>to transcript<span class="cursor-mark" aria-hidden="true">_</span></h2><p>Build the pieces in Python, run the task, and inspect the result.</p></div>
  </div>
  <div class="workflow-grid">
    <article><span class="workflow-icon" aria-hidden="true">[ + ]</span><p class="item-number">01 / DEFINE</p><h3>Write a task</h3><p>Give the agent instructions, data and tools. Choose how its work will be scored.</p></article>
    <article><span class="workflow-icon" aria-hidden="true">&gt;_</span><p class="item-number">02 / RUN</p><h3>Run in isolation</h3><p>Use a supported container or virtual machine runtime to run the environment.</p></article>
    <article><span class="workflow-icon" aria-hidden="true">{ : }</span><p class="item-number">03 / INSPECT</p><h3>See what happened</h3><p>Review scores, tool calls and transcripts in the terminal dashboard or saved files.</p></article>
  </div>
</section>

<section class="featured-section site-shell" aria-labelledby="featured-task-title">
  <div class="featured-copy">
    <p class="section-kicker">[ FEATURED TASK / MATHEMATICS ]</p>
    <h2 id="featured-task-title">A proof in Lean<span class="cursor-mark" aria-hidden="true">_</span></h2>
    <p>An agent works on a mathematical proof, and Lean checks the result. This experimental task is adapted from OpenAI's math collection, packaged by FineEnvs.</p>
    <a class="inline-link" href="/__chalk_docs__/environments/lean-math/">EXPLORE THE TASK <span aria-hidden="true">↗</span></a>
  </div>
  <div class="featured-card">
    <div class="featured-card-top"><span>FINITE CONGRUENCE GRAPH</span><span>EXPERIMENTAL</span></div>
    <dl>
      <div><dt>WORK</dt><dd>Complete a Lean proof</dd></div>
      <div><dt>CHECK</dt><dd>Upstream Comparator</dd></div>
      <div><dt>REWARD</dt><dd>1 if the proof passes; otherwise 0</dd></div>
    </dl>
    <p>One task is available in the <code>lean-math</code> template.</p>
  </div>
</section>

<section class="example-section site-shell">
  <div class="example-copy">
    <p class="section-kicker">[ 03 / START HERE ]</p>
    <h2>Start with<br>the example<span class="cursor-mark" aria-hidden="true">_</span></h2>
    <p>Create an environment from a local Chalk checkout. The example task asks an agent to find its Python executable and write the Python version to a file.</p>
    <a class="inline-link" href="/__chalk_docs__/getting-started/quick-start/">READ THE WALKTHROUGH <span aria-hidden="true">↗</span></a>
  </div>
  <div class="code-window" aria-label="Commands to install Chalk and create an environment">
    <div class="code-title"><span>+ TERMINAL</span><span>LOCAL CHECKOUT</span></div>
    <pre><code><span class="prompt">$</span> uv tool install .
<span class="prompt">$</span> chalk create-env my_env
<span class="prompt">$</span> cd my_env
<span class="prompt">$</span> uv sync --extra dev
<span class="prompt">$</span> uv run setup_data.py
<span class="prompt">$</span> uv run chalk tasks list</code></pre>
    <p>Use Linux or macOS (WSL on Windows). Running the task also requires a supported runtime and model configuration.</p>
  </div>
</section>

<section class="closing site-shell">
  <div><p class="section-kicker">[ 04 / YOUR TURN ]</p><h2>Make the next<br>task yours<span class="cursor-mark" aria-hidden="true">_</span></h2></div>
  <a class="action action-primary" href="/__chalk_docs__/getting-started/installation/">Installation guide <span aria-hidden="true">→</span></a>
</section>
<footer class="home-footer site-shell">
  <a class="footer-brand" href="/__chalk_home__/" aria-label="Chalk home"><img src="assets/chalk-logo.png" alt="Chalk"></a>
  <span>RL ENVIRONMENTS FOR CODING AND MATHEMATICAL REASONING.</span>
  <a href="/__chalk_docs__/credits/">CREDITS &amp; LICENSES ↗</a>
</footer>
</div>
