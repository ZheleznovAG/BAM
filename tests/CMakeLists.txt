add_executable(test_init test_init.cpp)

target_include_directories(test_init PRIVATE ${PROJECT_SOURCE_DIR}/CODE/SRC ${PROJECT_SOURCE_DIR}/CODE/TIGRE)

target_link_libraries(test_init PRIVATE SDL2::SDL2 tigre)

target_compile_definitions(test_init PRIVATE TEST_ASSET_DIR="${PROJECT_SOURCE_DIR}")
target_compile_definitions(test_init PRIVATE OS_SDL)

add_test(NAME test_init COMMAND test_init)
