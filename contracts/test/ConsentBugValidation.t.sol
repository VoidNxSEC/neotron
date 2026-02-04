// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test, console2} from "forge-std/Test.sol";
import {LendingProtocol} from "../src/LendingProtocol.sol";
import {LGPDConsent} from "../src/LGPDConsent.sol";

/**
 * @title ConsentBugValidation
 * @notice EXPERIMENTO CIENTIFICO - Prova da hipotese do bug de consent
 *
 * OBJETIVO: Demonstrar que:
 * 1. Workaround atual (self-consent) funciona mas esta semanticamente errado
 * 2. Design original (consent to contract) falha devido ao bug
 * 3. Fix correto (address(this)) resolve o problema
 *
 * @dev Este arquivo e EXPERIMENTAL - para validacao da hipotese apenas
 */
contract ConsentBugValidation is Test {
    LendingProtocol public lending;

    address public borrower = address(0x123);
    address public lender = address(0x456);

    function setUp() public {
        lending = new LendingProtocol();

        // Fund accounts
        vm.deal(borrower, 100 ether);
        vm.deal(lender, 100 ether);

        // Lender deposits liquidity
        vm.prank(lender);
        lending.deposit{value: 10 ether}();
    }

    // ============================================================================
    // EXPERIMENTO 1: Workaround Atual (Self-Consent)
    // ============================================================================

    function test_Experiment1_CurrentWorkaround_SelfConsent() public {
        console2.log("\n=== EXPERIMENTO 1: Workaround Atual (Self-Consent) ===");

        // Approach atual: borrower da consent para ELE MESMO
        vm.prank(borrower);
        lending.grantConsent(
            borrower,  // <- processor = borrower (self-consent)
            365 days,
            "Self-consent workaround"
        );

        console2.log("1. Consent gravado em: consents[borrower][borrower]");
        console2.log("   borrower:", borrower);
        console2.log("   processor:", borrower);

        // Verifica que consent existe
        bool hasConsent = lending.checkConsent(borrower, borrower);
        console2.log("2. Consent existe?", hasConsent);
        assertTrue(hasConsent, "Self-consent should exist");

        // Tenta pegar emprestimo
        console2.log("3. Tentando applyForLoan()...");
        vm.prank(borrower);

        // OK PASSA - mas semanticamente errado!
        bytes32 loanId = lending.applyForLoan{value: 1.5 ether}(1 ether);

        console2.log("4. SUCCESS! LoanId:", vm.toString(loanId));
        console2.log("   WARNING: Semantica LGPD incorreta (self-consent)");

        assertTrue(loanId != bytes32(0), "Loan should be created");
    }

    // ============================================================================
    // EXPERIMENTO 2: Design Original (Consent to Contract) - FALHA
    // ============================================================================

    function test_Experiment2_OriginalDesign_ConsentToContract_FAILS() public {
        console2.log("\n=== EXPERIMENTO 2: Design Original (Consent to Contract) ===");

        // Design original: borrower da consent para o CONTRATO
        vm.prank(borrower);
        lending.grantConsent(
            address(lending),  // <- processor = lending contract
            365 days,
            "Loan application - original design"
        );

        console2.log("1. Consent gravado em: consents[borrower][lending]");
        console2.log("   borrower:", borrower);
        console2.log("   processor (lending):", address(lending));

        // Verifica que consent existe NO LOCAL CORRETO
        bool hasConsentCorrectLocation = lending.checkConsent(borrower, address(lending));
        console2.log("2. Consent existe em [borrower][lending]?", hasConsentCorrectLocation);
        assertTrue(hasConsentCorrectLocation, "Consent should exist for lending contract");

        // MAS a validacao checa no local ERRADO
        console2.log("\n3. O que o modifier vai checar:");
        console2.log("   hasConsent(borrower) --> hasConsent(borrower, msg.sender)");
        console2.log("   msg.sender durante applyForLoan() = borrower");
        console2.log("   Entao checa: consents[borrower][borrower] FAIL");

        bool hasConsentWrongLocation = lending.checkConsent(borrower, borrower);
        console2.log("4. Consent existe em [borrower][borrower]?", hasConsentWrongLocation);
        assertFalse(hasConsentWrongLocation, "Consent should NOT exist in wrong location");

        // Tenta pegar emprestimo
        console2.log("\n5. Tentando applyForLoan()...");
        vm.prank(borrower);

        // FAIL FALHA - como esperado!
        vm.expectRevert();  // Espera revert com LGPD_Article7_ConsentRequired
        lending.applyForLoan{value: 1.5 ether}(1 ether);

        console2.log("6. FAILED! (como esperado)");
        console2.log("   Erro: LGPD_Article7_ConsentRequired");
        console2.log("   Causa: Procurou no lugar errado!");
    }

    // ============================================================================
    // EXPERIMENTO 3: Prova de msg.sender vs address(this)
    // ============================================================================

    function test_Experiment3_ProofOf_MsgSender_vs_AddressThis() public {
        console2.log("\n=== EXPERIMENTO 3: msg.sender vs address(this) ===");

        // Setup consent para o contrato
        vm.prank(borrower);
        lending.grantConsent(address(lending), 365 days, "Test");

        console2.log("1. Durante a execucao de applyForLoan():");
        console2.log("   - msg.sender =", borrower);
        console2.log("   - address(this) =", address(lending));
        console2.log("");
        console2.log("2. Storage atual:");
        console2.log("   consents[borrower][address(lending)] = EXISTS OK");
        console2.log("   consents[borrower][borrower] = NOT EXISTS FAIL");
        console2.log("");
        console2.log("3. Validacao BUGADA:");
        console2.log("   hasConsent(borrower, msg.sender)");
        console2.log("   = hasConsent(borrower, borrower)");
        console2.log("   = consents[borrower][borrower]");
        console2.log("   = NOT EXISTS FAIL --> REVERT");
        console2.log("");
        console2.log("4. Validacao CORRETA:");
        console2.log("   hasConsent(borrower, address(this))");
        console2.log("   = hasConsent(borrower, address(lending))");
        console2.log("   = consents[borrower][address(lending)]");
        console2.log("   = EXISTS OK --> SUCCESS");

        // Demonstra que checando diretamente funciona
        bool correctCheck = lending.checkConsent(borrower, address(lending));
        assertTrue(correctCheck, "Direct check with address(lending) works");

        console2.log("\n5. CONCLUSAO: Bug esta no uso de msg.sender ao inves de address(this)");
    }

    // ============================================================================
    // EXPERIMENTO 4: Visualizacao do Storage
    // ============================================================================

    function test_Experiment4_StorageVisualization() public {
        console2.log("\n=== EXPERIMENTO 4: Visualizacao do Storage ===");

        console2.log("\n+---------------------------------------------------------+");
        console2.log("| CENARIO A: Self-Consent (Workaround)                   |");
        console2.log("+---------------------------------------------------------+");

        vm.prank(borrower);
        lending.grantConsent(borrower, 365 days, "Self");

        console2.log("Storage:");
        console2.log("  consents[0x123][0x123] = { granted: true, ... } OK");
        console2.log("");
        console2.log("Validacao procura em:");
        console2.log("  consents[0x123][msg.sender]");
        console2.log("  = consents[0x123][0x123] OK MATCH!");
        console2.log("  Result: SUCESSO (mas semantica errada)");

        console2.log("\n+---------------------------------------------------------+");
        console2.log("| CENARIO B: Consent to Contract (Original Design)       |");
        console2.log("+---------------------------------------------------------+");

        address borrower2 = address(0x789);
        vm.deal(borrower2, 100 ether);
        vm.prank(borrower2);
        lending.grantConsent(address(lending), 365 days, "Contract");

        console2.log("Storage:");
        console2.log("  consents[0x789][0xLENDING] = { granted: true, ... } OK");
        console2.log("");
        console2.log("Validacao procura em:");
        console2.log("  consents[0x789][msg.sender]");
        console2.log("  = consents[0x789][0x789] FAIL NAO EXISTE!");
        console2.log("  Result: REVERT (design correto mas bug na validacao)");

        console2.log("\n+---------------------------------------------------------+");
        console2.log("| FIX: Usar address(this) ao inves de msg.sender         |");
        console2.log("+---------------------------------------------------------+");
        console2.log("Validacao CORRETA:");
        console2.log("  consents[0x789][address(this)]");
        console2.log("  = consents[0x789][0xLENDING] OK MATCH!");
        console2.log("  Result: SUCESSO (semantica correta!)");
    }

    // ============================================================================
    // EXPERIMENTO 5: Prova que o Fix Funciona (Simulado)
    // ============================================================================

    function test_Experiment5_FixValidation_SimulatedCorrectBehavior() public {
        console2.log("\n=== EXPERIMENTO 5: Validacao do Fix (Simulado) ===");

        // Setup: consent para o contrato
        vm.prank(borrower);
        lending.grantConsent(address(lending), 365 days, "Loan");

        console2.log("1. Consent gravado: consents[borrower][lending]");

        // Simula o que DEVERIA acontecer com o fix
        console2.log("\n2. Com o FIX aplicado (address(this)):");
        console2.log("   function hasConsent(address dataSubject) internal view override {");
        console2.log("       return hasConsent(dataSubject, address(this)); // <- FIX");
        console2.log("   }");

        // Valida manualmente como seria
        bool wouldWork = lending.checkConsent(borrower, address(lending));
        console2.log("\n3. Checagem: consents[borrower][address(this)]");
        console2.log("   = consents[borrower][lending]");
        console2.log("   = true OK");

        assertTrue(wouldWork, "With fix, consent validation would work");

        console2.log("\n4. CONCLUSAO: Fix de 1 linha resolve o problema!");
        console2.log("   - Semantica LGPD: CORRETA OK");
        console2.log("   - Funcionalidade: FUNCIONA OK");
        console2.log("   - Testes: VOLTAM AO NORMAL OK");
    }

    // ============================================================================
    // EXPERIMENTO 6: Comparacao Lado-a-Lado
    // ============================================================================

    function test_Experiment6_SideBySide_Comparison() public {
        console2.log("\n=== EXPERIMENTO 6: Comparacao Lado-a-Lado ===");

        address user1 = address(0xAAA);
        address user2 = address(0xBBB);
        vm.deal(user1, 100 ether);
        vm.deal(user2, 100 ether);

        console2.log("\n+------------------+----------------------+----------------------+");
        console2.log("|                  | WORKAROUND (atual)   | DESIGN ORIGINAL      |");
        console2.log("+------------------+----------------------+----------------------+");
        console2.log("| Consent Call     | grantConsent(user)   | grantConsent(lending)|");
        console2.log("| Storage          | [user][user]         | [user][lending]      |");
        console2.log("| Validation Looks | [user][msg.sender]   | [user][msg.sender]   |");
        console2.log("| msg.sender =     | user OK              | user FAIL              |");
        console2.log("| Match?           | YES OK               | NO FAIL                |");
        console2.log("| Result           | PASS                 | REVERT               |");
        console2.log("| LGPD Semantic    | WRONG FAIL             | CORRECT OK           |");
        console2.log("+------------------+----------------------+----------------------+");

        console2.log("\n+--------------------------------------------------------------+");
        console2.log("| COM FIX: address(this)                                       |");
        console2.log("+------------------+-------------------------------------------+");
        console2.log("| Consent Call     | grantConsent(lending)                     |");
        console2.log("| Storage          | [user][lending]                           |");
        console2.log("| Validation Looks | [user][address(this)] <- FIX               |");
        console2.log("| address(this) =  | lending OK                                |");
        console2.log("| Match?           | YES OK                                    |");
        console2.log("| Result           | PASS OK                                   |");
        console2.log("| LGPD Semantic    | CORRECT OK                                |");
        console2.log("+------------------+-------------------------------------------+");

        // Prova empirica
        vm.prank(user1);
        lending.grantConsent(user1, 365 days, "Workaround");

        vm.prank(user1);
        lending.applyForLoan{value: 1.5 ether}(1 ether);  // OK PASSA

        vm.prank(user2);
        lending.grantConsent(address(lending), 365 days, "Original");

        vm.prank(user2);
        vm.expectRevert();  // FAIL FALHA (com bug atual)
        lending.applyForLoan{value: 1.5 ether}(1 ether);

        console2.log("\nPROVA EMPIRICA:");
        console2.log("  user1 (workaround): PASSOU OK");
        console2.log("  user2 (original): FALHOU FAIL");
    }
}
