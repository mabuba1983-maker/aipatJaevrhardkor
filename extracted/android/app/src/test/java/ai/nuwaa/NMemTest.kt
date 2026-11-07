package ai.nuwaa

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Test

class NMemTest {
    @Test
    fun oldestRamMemorySpillsWhenLiveBudgetShrinks() {
        var budget = Long.MAX_VALUE
        val memory = NMem()
        memory.setBudgetProvider { budget }

        memory.add("abcdefghijklmno")
        val firstRecordBytes = memory.estimatedMemoryBytes()
        assertEquals(1, memory.activeRecordCount())
        assertNotNull(memory.dist("abcdefgh", 4))

        budget = firstRecordBytes + 1L
        memory.add("pqrstuvwxyz12345")

        assertEquals(1, memory.activeRecordCount())
        assertEquals(1L, memory.archivedFromRam)
        assertNull(memory.dist("abcdefgh", 4))
        assertNotNull(memory.dist("pqrstuvw", 4))
    }

    @Test
    fun zeroRamBudgetKeepsArchiveOutsideWorkingSet() {
        var budget = 0L
        val memory = NMem()
        memory.setBudgetProvider { budget }

        memory.add("remember this text")
        assertEquals(0, memory.activeRecordCount())
        assertEquals(1L, memory.archivedFromRam)

        budget = Long.MAX_VALUE
        memory.add("remember this text")
        assertEquals(1, memory.activeRecordCount())
        assertNotNull(memory.dist("remember", 4))
    }
}
