# Agent Harness Best Practices

**Ultimo Aggiornamento:** 2026-05-25
**Rilevanza per JARVIS:** Alta - Distilla pratiche operative da Everything Claude Code e Claude Code Best Practice per governare gli agenti del capability forge.

Questa pagina sintetizza pattern utili da [[Everything_Claude_Code]] e [[Claude_Code_Best_Practice]]. Non e' una proposta di installazione bulk: e' un set di pratiche da usare nel modo in cui Codex, Claude Code, OpenCode, Pi e altri harness lavorano su JARVIS.

## 1. Core Value / Funzione Principale

Il pattern centrale e':

```text
Research -> Plan -> Execute -> Review -> Verify -> Ship -> Learn
```

Ogni agente operativo dovrebbe:

- leggere il contesto minimo necessario;
- pianificare prima di editare;
- fare modifiche piccole e verificabili;
- usare test/lint/typecheck quando disponibili;
- chiedere review separata per modifiche rischiose;
- salvare insight utili in wiki/log/capability registry.

## 2. Specifiche Tecniche

Pattern da trattenere:

- **Commands vs Agents vs Skills**: command = workflow invocabile, agent = attore con contesto/permessi, skill = procedura riusabile caricata quando serve.
- **Manager/executor split**: manager traduce outcome in task graph, executor opera solo su subtask con capability allowlistata, budget e audit id.
- **Strategic compaction**: compattare dopo ricerca, milestone o debugging; evitare compaction a meta' implementazione.
- **Quality gate**: build/test/lint/typecheck/security prima di dichiarare completato.
- **Worktrees o staging**: lavori paralleli o rischiosi fuori dal runtime principale.
- **Security hooks**: bloccare accesso a `.env`, chiavi, token e file sensibili.
- **Cross-harness AGENTS.md**: mantenere istruzioni condivise ma leggere, senza gonfiare il contesto.
- **Model routing**: usare modelli premium solo per complessita' reale.
- **Dry-run/readiness**: prima di eseguire agent loop o subagent, produrre esito `ready/warning/blocked` con auth, tool, skill, MCP e percorsi risolti.
- **Review queue esplicita**: il risultato di un worker non e' completato finche non passa diff, test e owner/reviewer gate.

## 3. Integrazione con JARVIS

**Aggiunta di processo.**

Applicazione pratica:

- il capability forge usa sempre una mini-checklist `plan -> patch -> verify -> record`;
- i task grandi entrano in `Task Graph IR` o spec prima di essere implementati;
- gli agenti coding devono produrre evidenza: comandi eseguiti, file toccati, rischi residui;
- manager/executor e subagents vanno modellati come workflow governati, non come autonomia illimitata;
- le worktree sono il default per task paralleli o rischiosi del forge;
- ogni harness esterno deve passare un dry-run senza tool execution prima di accedere a repo reali;
- gli insight ricorrenti diventano skill o regole, ma solo dopo review.

Non installare automaticamente framework completi o hook globali da terzi. Prima audit, poi import selettivo.

## Relazioni

- [[Everything_Claude_Code]] - Catalogo esteso di agenti, skills, rules e hook.
- [[Claude_Code_Best_Practice]] - Osservatorio su feature e pratiche Claude Code.
- [[Verdent_Manager_Harness]] - Pattern manager/executor, task board e workspace isolation.
- [[OpenHarness]] - Harness con governance, skills, hooks, dry-run e swarm.
- [[Jarvis_Agentic_Architecture]] - Punto di integrazione runtime/forge.
- [[Code_Hygiene_Tools]] - Quality gate per codice.

**Fonti:** https://github.com/affaan-m/everything-claude-code, https://github.com/shanraisshan/claude-code-best-practice, `raw/scouting_2026_05_25_harness_emotion_sources.md`
