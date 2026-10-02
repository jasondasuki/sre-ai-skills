# Several links

Read this when the user pastes more than one Datadog link, or when several
alarms look related.

1. Parse and resolve all links first, in parallel, then print a short **intake
   table**: link -> type -> monitor/service -> group -> UTC time -> state.
2. **Deduplicate** (same monitor, same group, same time bucket is one alarm).
3. **Cluster** alarms by shared service, dependency, host/node, namespace,
   cluster, or overlapping time. Alarms that fire within the same few minutes on
   connected services are presumed to share a cause until the data says
   otherwise.
   - A cluster gets **one hypothesis tree**. Start with "one upstream cause
     explains all of these", and pick the earliest-firing alarm and the deepest
     dependency as the likely origin.
   - Unrelated alarms (different services, no dependency, no time overlap) each
     get their own tree. Run them one after another in the same report; do not
     force a link between them.
4. Order the investigation by **earliest T0 first** (causes precede symptoms),
   not by the order the links were pasted.
5. Say plainly in the report which alarms are symptoms of the root cause and
   which are independent.
