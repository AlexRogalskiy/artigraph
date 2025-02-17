import logging
from graphlib import TopologicalSorter

from arti.artifacts import Artifact
from arti.executors import Executor
from arti.graphs import Graph
from arti.producers import Producer


class LocalExecutor(Executor):
    # TODO: Should we separate .map and .build steps so we can:
    # - add "sync" / "dry run" sort of things
    # - parallelize build
    #
    # We may still want to repeat the .map phase in the future, if we wanted to support some sort of
    # iterated or cyclic Producers (eg: first pass output feeds into second run - in that case,
    # `.map` should describe how to "converge" by returning the same outputs as a prior call).

    def build(self, graph: Graph) -> None:
        # NOTE: Raw Artifacts will already be discovered and linked in the backend to this graph
        # snapshot.
        assert graph.snapshot_id is not None
        with graph.backend.connect() as backend:
            for node in TopologicalSorter(graph.dependencies).static_order():
                if isinstance(node, Artifact):
                    # TODO: Compute Statistics (if not already computed for the partition) and check
                    # Thresholds (every time, as they may be changed, dynamic, or overridden).
                    pass
                elif isinstance(node, Producer):
                    logging.info(f"Building {node}...")
                    input_partitions = self.get_producer_inputs(graph, backend, node)
                    (
                        partition_dependencies,
                        partition_input_fingerprints,
                    ) = node.compute_dependencies(input_partitions)
                    existing_keys = self.discover_producer_partitions(
                        graph,
                        backend,
                        node,
                        partition_input_fingerprints=partition_input_fingerprints,
                    )
                    for partition_key, dependencies in partition_dependencies.items():
                        self.build_producer_partition(
                            graph,
                            backend,
                            node,
                            existing_partition_keys=existing_keys,
                            input_fingerprint=partition_input_fingerprints[partition_key],
                            partition_dependencies=dependencies,
                            partition_key=partition_key,
                        )
                else:
                    raise NotImplementedError()
        logging.info("Build finished.")
