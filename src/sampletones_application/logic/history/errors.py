class UntrackedMutationError(RuntimeError):
    """Raised when a project mutation fires outside any history transaction.

    Under strict deployment the history refuses to guess a grouping for an
    unlabelled mutation and surfaces the completeness gap immediately, so the
    call site can be wrapped in a transaction.
    """


class HistoryIntegrityError(RuntimeError):
    """Raised when restoring a snapshot fails to reproduce its recorded fingerprint.

    Restoring a stored snapshot must yield a byte-identical project state; a
    mismatch means a snapshot shared mutable state with the live project, which
    breaks the reversibility guarantee.
    """
