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
        memory.add("pqrstuvwxyz1234")

        assertEquals(1, memory.activeRecordCount())
        assertEquals(1L, memory.archivedFromRam)
        assertNull(memory.dist("abcdefgh", 4))
        assertNotNull(memory.dist("pqrstuvw", 4))
    }

    @Test
    fun noFixedMemoryRecordCountWhenRamBudgetAllows() {
        val memory = NMem()
        memory.setBudgetProvider { Long.MAX_VALUE }
        repeat(1000) { memory.add("memory record number $it") }

        assertEquals(1000, memory.activeRecordCount())
    }

    @Test
    fun generationLookupRechecksShrinkingRamBudget() {
        var budget = Long.MAX_VALUE
        val memory = NMem()
        memory.setBudgetProvider { budget }
        memory.add("memory available during generation")
        assertNotNull(memory.dist("memory", 4))

        budget = 0L
        assertNull(memory.dist("memory", 4))
        assertEquals(0, memory.activeRecordCount())
        assertEquals(1L, memory.archivedFromRam)
    }

    @Test
    fun restoringNewestFirstKeepsNewestRecordWhenBudgetIsExceeded() {
        var budget = Long.MAX_VALUE
        val memory = NMem()
        memory.setBudgetProvider { budget }
        memory.addNewestFirst("newest archived memory")
        budget = memory.estimatedMemoryBytes() + 1L
        memory.addNewestFirst("older archived memory")

        assertEquals(1, memory.activeRecordCount())
        assertEquals(1L, memory.archivedFromRam)
        assertNotNull(memory.dist("newest", 4))
        assertNull(memory.dist("older", 4))
    }

    @Test
    fun repeatedMemoriesReinforceCountsWithoutLinearDuplicateFiltering() {
        val memory = NMem()
        memory.setBudgetProvider { Long.MAX_VALUE }
        memory.add("repeat this memory")
        memory.add("repeat this memory")

        assertEquals(2, memory.activeRecordCount())
        val distribution = memory.dist("repea", 4)
        assertNotNull(distribution)
        assertEquals(2, distribution!!.second['t'])
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
