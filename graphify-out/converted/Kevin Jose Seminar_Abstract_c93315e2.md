<!-- converted from Kevin Jose Seminar_Abstract.docx -->

# Title of the Seminar:
# Verification Methodologies for RISC-V Processors




## Abstract:

The open and extensible nature of the RISC-V instruction set architecture has driven rapid growth in custom processor implementations across both academia and industry. However, this same extensibility makes verification — establishing that a processor implementation actually behaves as its specification requires — substantially more complex and error-prone. This seminar surveys the principal methodologies used to verify RISC-V processors, organized around two questions: how verification tests are generated, and how correctness is decided. The base paper presents PATARA, a self-testing framework based on the REVERSI approach, which generates randomized test programs that verify their own execution without requiring an external golden reference model, reaching 100% code coverage on a pipelined RV32IM implementation and exposing hazard-related bugs that the official RISC-V compliance suite left undetected. The supporting literature covers the complementary technique families: formal verification through high-level model checking and through Binary Decision Diagram-based equivalence checking with proven complexity bounds; coverage-guided RTL fuzzing; and industrial UVM-based co-simulation against a golden reference model. A comparative analysis contrasts these approaches along the axes of test generation, correctness checking, scalability, and completeness of guarantee. The study is motivated by, and directly relevant to, the design and verification of custom instruction-set extensions for edge AI workloads, where the absence of a golden reference for newly-designed instructions makes the choice of verification methodology a central engineering concern.


Submitted by:	Approved by:
Name: Kevin Jose	Guide Name: Dr. Jomina John
UID: U2303131	Signature:
Class: CSE-Beta	Date: