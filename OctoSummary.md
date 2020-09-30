# Quick Instructions Summary

A short summary of all of the directives and statements supported by Octo.
Corresponding Chip8 pneumonics and opcodes are included, when relevant.

## Directives

* `: <labelname>` - Track address for call/jump resolution.
* `:alias <dstname> <srcreg>` - Track new register name
* `:call` - Track address for call/jump resolution.
* `:const <dstname> <srcnum>` - Add to constant table.
* `:calc name { <calcexpre> }` - Add to constant table.
* `:macro name args\* {}` - Save tokens and namelist. On emit, replay tokens, but with names subbed.
* `:next` - 
* `:org` - Update PC
* `:stringmode name "alphabet" {}` - 
* `:unpack MSB <addr>` -


## Statements

* `return` (also `;`) `RET (00EE)`
* `clear` `CLS (00E0)`
* `save cx` `LD [I], Vx (Fx55)`
* `load vx` `LD Vx, [I] (Fx65)`
* `bcd vx` `LD B, Vx (Fx33)`
* `sprite vx vy n` `DRW D, Vx, Vy, n (Dxyn)`
* `jump <addr>` `JP addr (1nnn)`
* `jump0 <addr>` `JP V0, addr (Bnnn)`
* `hires` `HIGH (00FF)`
* `lores` `LOW (00FE)`
* `scroll-down n` `SCD n (00Cn)` 
* `scroll-left` `SCL (00FB)`
* `scroll-right` `(SCR (00FC)`
* `exit` `EXIT (00FD)`
* `saveflags vx` `LD R, Vx (Fx75)`
* `loadflags vx` `LD Vx, R (Fx85)`


## Operations

### Special
* `delay := vx` `LD DT, Vx (Fx15)`
* `buzzer := vx` `LD ST, Vx (Fx18)`

### Index
* `i := <addr>` `LD I, addr (Annn)`
* `i += vx` `ADD I, Vx (Fx1E)`
* `i := hex vx` `LD F, Vx (Fx29)`
* `i := bighex vx` `LD HF, Vx (Fx30)`

## Register-Special
* `vx := random b` `RND Vx, b (Cxbb)`
* `vx := delay` `LD Vx, DT (Fx07)`
* `vx := key` `LD Vx, K (Fx0A)`

## Register-Const
* `vx := b` `LD Vx, bb (6xbb)`
* `vx += b` `ADD Vx, bb (7xbb)`
* `vx -= b` `ADD Vx, bb (7xbb)` (Two's complement of `b`)


## Register-Register
* `vx := vy` `LD Vx, Vy (8xy0)`
* `|= (OR 1)` `&= (AND 2)` `^= (XOR 3)` `+= (ADD 4)` 
* `-= (SUB 5)` `>>= (SHR 6)` `=- (NSUB 7)`  ` <<= (SHL E)`


# Conditionals

* `if <condtion> then <statement>`
* `if <condition> begin statement* else statement* end`

## Conditions
* `vx == b` `then -> SNE Vx, b (4xbb)`
* `vx != b` `then -> SE Vx, b (3xbb)`
* `vx == vy` `then -> SE Vx, Vy (5xy0)`
* `vx != vy` `then -> SNE Vx, Vy (9xy0)`
* `vx key` `then -> SKNP Vx (ExA1)`
* `vx !key` `then -> SKP Vx (Ex9E)`

```
X    Y     X - Y  VF    Y - X  VF   X > Y  X < Y  X >= Y  X <= Y
1    2      -1    0       1    1      0     1       0       1
1    1       0    1       0    1      0     0       1       1
2    1       1    1       -1   0      1     0       1       0
```
Before each comparison, `LD VF, b (6Fbb)`
* `vx < b` `then -> NSUB VF, Vx; SNE VF, 0 (8Fx7 3F00)`
* `vx > b` `then -> SUB VF, Vx; SNE VF, 0 (8Fx7 3F00)`
* `vx <= b` `then -> SUB VF, Vx; SE VF, 0 (8Fx7 3F00)`
* `vx >= b` `then -> NSUB VF, Vx; SE VF,  (8Fx7 3F00)0`

Before each comparison, `LD VF, Vy (8xy0)`
* `vx < vy` `then -> NSUB VF, Vx; SNE VF, 0 (8Fx7 4F00)`
* `vx > vy` `then -> SUB VF, Vx; SNE VF, 0 (8Fx5 4F00)`
* `vx <= vy` `then -> SUB VF, Vx; SE VF, 0 (8Fx5 3F00)`
* `vx >= vy` `then -> NSUB VF, Vx; SE VF, 0 (8Fx7 3F00)`

* `begin` -> use dual of op above, and after `SE/SNE` emit `JMP <else/end> (1aaa)`
  * Duals: 
    * `==` <-> `!=`
    * `<` <-> `>=`
    * `>` <-> `<=`
    * `key` <-> `-key`
  * Jump will be resolved later on reaching `else` or `end`

* `else` -> Resolve `if` `JMP`, emit `JMP <end> (1aaa)`
  * Jump will be resolve on end

* `end` -> Resolve `if` `JMP`

## Calc ops

Right-to-left eval with () groupings
No operator precedence.

* unary:  - ~ ! sin cos tan exp log abs sqrt sign ceil floor @ strlen
* binary: - + * / % & | ^ << >> pow min max < <= == != >= >
* constants: E PI HERE


